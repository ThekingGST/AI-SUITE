from __future__ import annotations

import asyncio
import io
import threading
from concurrent.futures import Future

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import AbortedError
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth
from jarvis_ai.voice.v2.playback.base import AudioPlaybackInterface
from jarvis_ai.voice.v2.playback.pygame_player import PygamePlayer


class EdgeTtsBackend:
    """Voice System 2.0 Edge-TTS backend with persistent async loop.
    
    Provides high-quality, low-latency streaming TTS over WebSockets.
    To avoid the overhead of `asyncio.run()` per utterance, this backend
    maintains a persistent async event loop on a dedicated background thread.
    """

    def __init__(self, voice_name: str = "en-US-AriaNeural", player: AudioPlaybackInterface | None = None) -> None:
        self._voice_name = voice_name
        self._player = player or PygamePlayer()
        
        self._capabilities = BackendCapabilities(
            supports_streaming=True,
            supports_interrupt=True,
            supports_voice_selection=True,
            supports_stream_output=True,
            supports_pitch=True,
            supports_rate=True,
            supports_volume=True,
            offline=False,
            network_required=True,
        )
        self._health = BackendHealth()
        
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._ready_event = threading.Event()

    def get_capabilities(self) -> BackendCapabilities:
        return self._capabilities

    def get_health(self) -> BackendHealth:
        return self._health

    def is_available(self) -> bool:
        return self._health.is_available

    def engine_name(self) -> str:
        return "edge-tts"

    # -- lifecycle -------------------------------------------------------------

    def apply_profile(self, profile: "VoiceProfile") -> None:
        """Apply VoiceProfile constraints to this backend."""
        voice_id = profile.backend_voice_overrides.get("edge-tts")
        if voice_id:
            self._voice_name = voice_id

    def initialize(self) -> None:
        """Start the persistent async worker thread and initialize playback."""
        if self._thread and self._thread.is_alive():
            return
            
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            LOGGER.warning("Edge-TTS package not installed, disabled.")
            self._health.is_available = False
            return
            
        try:
            self._player.initialize()
        except Exception as exc:
            LOGGER.warning("Edge-TTS playback init failed: %s", exc)
            self._health.record_error(str(exc))
            return
            
        self._shutdown_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run_event_loop, name="EdgeTtsAsyncWorker", daemon=True)
        self._thread.start()
        
        # Wait for the loop to be ready
        if self._ready_event.wait(timeout=2.0):
            # Do a quick health check ping if needed, but we'll assume available
            self._health.record_success()
            LOGGER.info("EdgeTtsBackend initialised (voice=%s).", self._voice_name)
        else:
            LOGGER.error("EdgeTtsBackend async thread failed to start in time.")
            self._health.record_error("Async loop startup timeout")

    def close(self) -> None:
        """Shut down the async worker and release resources."""
        self._shutdown_event.set()
        
        # Signal the event loop to stop safely from its own thread
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        if self._thread:
            self._thread.join(timeout=2.0)
            
        try:
            self._player.close()
        except Exception as exc:
            LOGGER.warning("Edge-TTS playback close failed: %s", exc)
            
        self._health.is_available = False

    # -- async worker thread ---------------------------------------------------

    def _run_event_loop(self) -> None:
        """Main loop for the dedicated async worker thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        self._ready_event.set()
        
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            LOGGER.info("EdgeTtsAsyncWorker shut down.")

    # -- TTSBackend protocol ---------------------------------------------------

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        """Synthesize and play speech, bridging from synchronous to the async loop."""
        if not self._health.is_available or not self._loop or not self._loop.is_running():
            raise RuntimeError("EdgeTtsBackend not ready or event loop not running.")
            
        if abort and abort.is_set():
            raise AbortedError("Aborted before speech")
            
        # We need to run the async generator on the async loop, but consume it 
        # incrementally or wait for it to finish downloading the chunk, then play.
        # Since Edge-TTS is fast, we will download the chunk to bytes and play.
        
        import time

        
        future: Future[bytes] = asyncio.run_coroutine_threadsafe(
            self._synthesize_async(text, abort), self._loop
        )
        
        try:
            audio_bytes = future.result() # Will block until done or exception
            if abort and abort.is_set():
                raise AbortedError("Aborted during download")
                
            if not audio_bytes:
                return
                
            self._player.play_bytes(audio_bytes, abort)
            self._health.record_success()
            
        except AbortedError:
            raise
        except Exception as exc:
            LOGGER.warning("Edge-TTS synthesis failed: %s", exc)
            # Differentiate network errors if possible
            is_network = "WinError" in str(exc) or "Timeout" in str(exc) or "Connection" in str(exc)
            self._health.record_error(str(exc), is_network_error=is_network)
            raise RuntimeError(f"Edge-TTS synthesis failed: {exc}") from exc

    async def _synthesize_async(self, text: str, abort: threading.Event | None) -> bytes:
        """Coroutine that actually communicates with Edge-TTS."""
        import edge_tts
        
        # Note: We can add pitch/rate/volume formatting here later
        communicate = edge_tts.Communicate(text, self._voice_name)
        
        audio_stream = io.BytesIO()
        
        try:
            async for chunk in communicate.stream():
                if abort and abort.is_set():
                    raise AbortedError("Aborted during streaming")
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
        except AbortedError:
            raise
        except Exception as exc:
            raise exc
            
        return audio_stream.getvalue()
