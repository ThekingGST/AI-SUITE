from __future__ import annotations

import abc
from typing import Optional

from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.events import AudioEventBus


class AudioProcessor(abc.ABC):
    """Base class for all audio pipeline processors."""

    def __init__(self) -> None:
        self.next_processor: Optional[AudioProcessor] = None
        self.event_bus: Optional[AudioEventBus] = None

    def set_next(self, processor: AudioProcessor) -> AudioProcessor:
        """Link the next processor in the chain and return it for fluent chaining."""
        self.next_processor = processor
        if self.event_bus:
            processor.set_event_bus(self.event_bus)
        return processor
        
    def set_event_bus(self, event_bus: AudioEventBus) -> None:
        """Inject the event bus into this processor and all subsequent processors."""
        self.event_bus = event_bus
        if self.next_processor:
            self.next_processor.set_event_bus(event_bus)

    @abc.abstractmethod
    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        """Process an audio frame. 
        
        Returns the modified frame, or None if the frame is consumed/dropped.
        """
        pass

    def pass_to_next(self, frame: AudioFrame) -> Optional[AudioFrame]:
        """Pass the frame to the next processor in the chain."""
        if self.next_processor:
            import threading
            import time
            from jarvis_ai.utils.logger import LOGGER

            return self.next_processor.process(frame)
        return frame


class PassThroughProcessor(AudioProcessor):
    """A placeholder processor that simply passes the audio frame unmodified."""
    
    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        # E.g. Future implementation of Noise Suppression, AEC, etc.
        return self.pass_to_next(frame)


class ProcessorChain:
    """Manages the execution of the audio processing pipeline."""

    def __init__(self, event_bus: AudioEventBus) -> None:
        self.event_bus = event_bus
        self.head: Optional[AudioProcessor] = None

    def build_chain(self, *processors: AudioProcessor) -> None:
        """Construct the processing chain from a list of processors."""
        if not processors:
            self.head = None
            return

        self.head = processors[0]
        self.head.set_event_bus(self.event_bus)
        
        current = self.head
        for p in processors[1:]:
            current = current.set_next(p)
            
    def process(self, frame: AudioFrame) -> None:
        """Feed a raw frame into the pipeline."""
        if self.head:
            self.head.process(frame)
