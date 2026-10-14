from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional

import pyaudio

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.events import AudioEvent, AudioEventBus
from jarvis_ai.voice.input.device_manager import AudioDeviceManager


@dataclass
class AudioFrame:
    """A single raw audio frame with metadata."""
    data: bytes
    timestamp: float
    frame_count: int
    is_speech: bool = True  # Default True so STT processes it if no VAD is present


class AudioCaptureWorker:
    """A dedicated thread for reading raw audio bytes safely."""

    def __init__(self, event_bus: AudioEventBus, device_manager: AudioDeviceManager, 
                 sample_rate: int = 16000, frame_size: int = 1024, max_queue_size: int = 50) -> None:
        self._event_bus = event_bus
        self._device_manager = device_manager
        
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        
        # Max queue size of 50 chunks (at 16kHz, 1024 frames = 64ms per chunk) 
        # 50 chunks = 3.2 seconds of buffer to prevent memory leaks if processing lags.
        self._queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=max_queue_size)
        
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        
    def start(self) -> bool:
        """Start the capture worker thread."""
        if self._thread and self._thread.is_alive():
            self.resume()
            return True
            
        active_device = self._device_manager.get_active_device()
        if not active_device:
            LOGGER.error("AudioCaptureWorker: No active device found.")
            return False
            
        # Ensure device manager has initialized PyAudio
        if not self._device_manager._pyaudio:
            LOGGER.error("AudioCaptureWorker: DeviceManager pyaudio not initialized.")
            return False

        self._stop_event.clear()
        self._paused.clear()
        
        # Drain existing queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
                
        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(active_device.index,),
            name="AudioCaptureWorker",
            daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """Gracefully stop capture."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
            
    def pause(self) -> None:
        """Pause capture (drain audio but ignore it)."""
        self._paused.set()
        
    def resume(self) -> None:
        """Resume capture."""
        self._paused.clear()
        if not self._thread or not self._thread.is_alive():
            LOGGER.warning("AudioCaptureWorker: Thread dead on resume, restarting...")
            self.start()
        
    def get_frame(self, timeout: float = 0.1) -> Optional[AudioFrame]:
        """Fetch the next available audio frame from the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _capture_loop(self, device_index: int) -> None:
        """The main capture loop."""
        LOGGER.info("Starting AudioCaptureWorker...")
        p = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.frame_size,
            )
            
            LOGGER.info(f"Stream opened on device {device_index}")
            self._event_bus.emit(AudioEvent.AUDIO_STARTED)
            
            LOGGER.info("[AUDIO] microphone initialized")
            
            import numpy as np
            while not self._stop_event.is_set():
                try:
                    # exception_on_overflow=False handles minor underflows silently
                    data = stream.read(self.frame_size, exception_on_overflow=False)
                    
                    if self._paused.is_set():
                        continue
                        
                    # DIAGNOSTICS
                    if len(data) > 0:
                        audio_np = np.frombuffer(data, dtype=np.int16)
                        rms = np.sqrt(np.mean(np.square(audio_np.astype(np.float32)))) if len(audio_np) > 0 else 0.0
                        peak = np.max(np.abs(audio_np)) if len(audio_np) > 0 else 0
                        if np.random.random() < 0.05: # Sample 5% of frames for logging
                            LOGGER.info(f"[AUDIO] frame received: {len(audio_np)} samples | RMS: {rms:.4f} | peak: {peak}")
                        
                    frame = AudioFrame(
                        data=data,
                        timestamp=time.time(),
                        frame_count=self.frame_size
                    )
                    
                    try:
                        self._queue.put_nowait(frame)
                    except queue.Full:
                        # Overflow protection: Drop oldest frame
                        try:
                            self._queue.get_nowait()
                            self._queue.put_nowait(frame)
                            LOGGER.warning("AudioCaptureWorker: Queue overflow, dropping oldest frame.")
                        except queue.Empty:
                            pass
                        
                except OSError as exc:
                    LOGGER.error("AudioCaptureWorker: Stream read error: %s", exc)
                    self._event_bus.emit(AudioEvent.DEVICE_ERROR, {"error": str(exc)})
                    break
                    
        except Exception as exc:
            LOGGER.error("AudioCaptureWorker: Failed to open stream: %s", exc)
            self._event_bus.emit(AudioEvent.DEVICE_ERROR, {"error": str(exc)})
            
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            LOGGER.info("AudioCaptureWorker: Stream closed.")
            self._event_bus.emit(AudioEvent.AUDIO_STOPPED)
