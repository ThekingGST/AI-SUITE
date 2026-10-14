from __future__ import annotations

import abc
from typing import Optional

from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.events import AudioEvent
from jarvis_ai.voice.input.pipeline import AudioProcessor
from jarvis_ai.voice.input.profile import AudioProfile


class STTBackend(AudioProcessor, abc.ABC):
    """Base class for streaming Speech-to-Text backends.
    
    STT backends typically consume audio frames and emit transcription events.
    """

    def __init__(self, profile: AudioProfile) -> None:
        super().__init__()
        self.profile = profile
        self.is_recognizing = False
        # VAD typically takes ~200-400ms to trigger.
        # We buffer the last ~640ms (10 frames at 64ms each) of audio.
        import collections
        self._pre_speech_buffer = collections.deque(maxlen=10)

    def update_profile(self, profile: AudioProfile) -> None:
        self.profile = profile

    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        """Process an audio frame and return it (or None if consumed)."""
        is_speech = getattr(frame, "is_speech", True)
        
        if is_speech:
            if not self.is_recognizing:
                self.is_recognizing = True
                if self.event_bus:
                    self.event_bus.emit(AudioEvent.RECOGNITION_STARTED, {"timestamp": frame.timestamp})
                
                # Flush the pre-speech buffer into the STT engine
                # so we don't clip the beginning of the utterance.
                while self._pre_speech_buffer:
                    buffered_data = self._pre_speech_buffer.popleft()
                    self.process_audio_chunk(buffered_data)
            
            # Process the current live frame
            self.process_audio_chunk(frame.data)
        else:
            # Buffer the frame in case VAD triggers in the next few hundred milliseconds
            self._pre_speech_buffer.append(frame.data)
            
            if self.is_recognizing:
                self.is_recognizing = False
                self.finalize_recognition()
                self._pre_speech_buffer.clear()
                
        return self.pass_to_next(frame)

    @abc.abstractmethod
    def process_audio_chunk(self, data: bytes) -> None:
        """Process a raw chunk of audio bytes."""
        pass
        
    @abc.abstractmethod
    def finalize_recognition(self) -> None:
        """Force the STT backend to finalize and emit the current transcription."""
        pass
