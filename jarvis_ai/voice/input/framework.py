from __future__ import annotations

import threading
from typing import Optional

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.capture import AudioCaptureWorker, AudioFrame
from jarvis_ai.voice.input.device_manager import AudioDeviceManager
from jarvis_ai.voice.input.events import AudioEventBus
from jarvis_ai.voice.input.pipeline import ProcessorChain, PassThroughProcessor
from jarvis_ai.voice.input.profile import DEFAULT_PROFILES, AudioProfile
from jarvis_ai.voice.input.state import AudioStateMachine
from jarvis_ai.voice.input.stt.vosk_backend import VOSK_AVAILABLE, VoskBackend
from jarvis_ai.voice.input.vad import create_vad
from jarvis_ai.voice.input.wakeword import OPENWAKEWORD_AVAILABLE, WakeWordEngine


class AudioInputFramework:
    """The central orchestrator for the AI Suite Audio Input Framework."""

    def __init__(self, profile_name: str = "office") -> None:
        self.profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["office"])
        
        # 1. Event Bus
        self.event_bus = AudioEventBus()
        
        # 2. State Machine
        self.state_machine = AudioStateMachine(self.event_bus)
        
        # 3. Hardware Capture
        self.device_manager = AudioDeviceManager(self.event_bus)
        self.capture_worker = AudioCaptureWorker(
            event_bus=self.event_bus,
            device_manager=self.device_manager,
            sample_rate=CONFIG.voice.sample_rate,
            frame_size=CONFIG.voice.frame_size
        )
        
        # 4. Processing Pipeline
        self.pipeline = ProcessorChain(self.event_bus)
        
        # Build the processor chain
        vad = create_vad(self.profile, sample_rate=CONFIG.voice.sample_rate)
        wakeword = WakeWordEngine(self.profile, wake_words=[CONFIG.voice.wake_word])
        
        processors = [
            PassThroughProcessor(),  # Placeholder for Noise Suppression
            PassThroughProcessor(),  # Placeholder for AEC
            vad,
            wakeword
        ]
        
        if VOSK_AVAILABLE:
            stt = VoskBackend(self.profile, sample_rate=CONFIG.voice.sample_rate)
            processors.append(stt)
        else:
            LOGGER.warning("AudioInputFramework: Vosk is not available. STT disabled.")
            
        self.pipeline.build_chain(*processors)
        
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self) -> None:
        """Start hardware monitoring, capture, and pipeline threads."""
        self.device_manager.start()
        success = self.capture_worker.start()
        if not success:
            LOGGER.error("AudioInputFramework: Failed to start capture worker.")
            return
            
        self._stop_event.clear()
        if not self._processing_thread or not self._processing_thread.is_alive():
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                name="AudioPipelineWorker",
                daemon=True
            )
            self._processing_thread.start()
            
    def stop(self) -> None:
        """Gracefully stop all input processing."""
        self._stop_event.set()
        self.capture_worker.stop()
        self.device_manager.stop()
        if self._processing_thread:
            self._processing_thread.join(timeout=2.0)
            
    def pause(self) -> None:
        """Pause capture (drain audio but ignore it)."""
        self.capture_worker.pause()
        
    def resume(self) -> None:
        """Resume capture."""
        self.capture_worker.resume()
        if not self._processing_thread or not self._processing_thread.is_alive():
            LOGGER.warning("AudioInputFramework: Pipeline thread dead on resume, restarting...")
            self._stop_event.clear()
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                name="AudioPipelineWorker",
                daemon=True
            )
            self._processing_thread.start()
        
    def set_profile(self, profile_name: str) -> None:
        """Dynamically update the active audio profile."""
        if profile_name in DEFAULT_PROFILES:
            self.profile = DEFAULT_PROFILES[profile_name]
            # Ideally propagate to processors
            current = self.pipeline.head
            while current:
                if hasattr(current, 'update_profile'):
                    current.update_profile(self.profile)
                current = current.next_processor
            LOGGER.info("AudioInputFramework: Switched profile to '%s'", profile_name)

    def _processing_loop(self) -> None:
        """Pull raw frames from capture worker and push through the pipeline."""
        trace_count = 0
        while not self._stop_event.is_set():
            frame = self.capture_worker.get_frame(timeout=0.1)
            if frame:
                trace_count += 1
                if trace_count % 15 == 0:
                    LOGGER.info("AudioPipeline:\nFrame accepted")
                try:
                    self.pipeline.process(frame)
                except Exception as exc:
                    LOGGER.error("AudioInputFramework: Pipeline processing error: %s", exc, exc_info=True)
