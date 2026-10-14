from __future__ import annotations

import time
import numpy as np
from pathlib import Path

from jarvis_ai.config import CONFIG, MODELS_DIR
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.events import AudioEvent
from jarvis_ai.voice.input.profile import AudioProfile
from jarvis_ai.voice.input.stt.base import STTBackend

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

class FasterWhisperBackend(STTBackend):
    def __init__(self, profile: AudioProfile, sample_rate: int = 16000, model_size: str = 'large-v3-turbo', device: str = 'auto', compute_type: str = 'int8') -> None:
        super().__init__(profile)
        self.sample_rate = sample_rate
        self.model_size = model_size
        
        if not FASTER_WHISPER_AVAILABLE:
            LOGGER.warning("faster_whisper is not installed.")
        
        if device == 'auto':
            try:
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except ImportError:
                self.device = 'cpu'
        else:
            self.device = device
            
        self.compute_type = compute_type

        self._model = None
        self._audio_buffer = bytearray()
        
    def _load_model(self) -> None:
        if self._model is not None:
            return
            
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError("faster_whisper is not available")
            
        start_time = time.time()
        
        model_path = str(MODELS_DIR / "stt" / "whisper" / self.model_size)
        if not Path(model_path).exists():
            model_path = self.model_size # fallback to download
            
        try:
            self._model = WhisperModel(model_path, device=self.device, compute_type=self.compute_type)
            load_time = time.time() - start_time
            LOGGER.info(f"FasterWhisperBackend loaded model {self.model_size} on {self.device} in {load_time:.2f}s")
        except Exception as e:
            LOGGER.error(f"Failed to load FasterWhisper model: {e}")
            raise RuntimeError(f"Failed to load model: {e}")

    def process_audio_chunk(self, data: bytes) -> None:
        self._audio_buffer.extend(data)
        
    def set_language(self, language: str) -> None:
        self.preferred_language = language if language != 'auto' else None

    def finalize_recognition(self) -> None:
        if not self._audio_buffer:
            return
            
        try:
            self._load_model()
            
            # Convert audio
            audio_np = np.frombuffer(bytes(self._audio_buffer), dtype=np.int16).astype(np.float32) / 32768.0
            audio_duration = len(audio_np) / self.sample_rate
            self._audio_buffer.clear()
            
            LOGGER.info(f"[STT] audio received: {len(audio_np)} samples")
            LOGGER.info(f"[STT] audio duration: {audio_duration:.2f}s")
            LOGGER.info("[STT] transcription started")
            
            start_time = time.time()
            lang = getattr(self, 'preferred_language', None)
            
            # Decode using robust parameters for short multi-lingual commands
            segments, info = self._model.transcribe(
                audio_np, 
                language=lang,
                task="transcribe",
                beam_size=5,
                temperature=[0.0, 0.2, 0.4, 0.6],
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                log_prob_threshold=-1.0
            )
            
            text = "".join(segment.text for segment in segments).strip()
            transcription_time = time.time() - start_time
            
            LOGGER.info("[STT] transcription completed")
            
            mode_str = "FORCED" if lang else "AUTO"
            LOGGER.info(f"[STT] Backend: faster-whisper")
            if lang:
                LOGGER.info(f"[STT] Requested language: {lang}")
            LOGGER.info(f"[STT] Language mode: {mode_str}")
            LOGGER.info(f"[STT] Detected language: {info.language}")
            LOGGER.info(f"[STT] Confidence: {info.language_probability:.2f}")
            LOGGER.info(f"[STT] Raw text: {text}")
            
            if text and getattr(self, 'event_bus', None):
                self.event_bus.emit(AudioEvent.RECOGNITION_FINISHED, {
                    'text': text, 
                    'language': info.language,
                    'language_confidence': info.language_probability
                })
        except Exception as e:
            LOGGER.error(f"FasterWhisperBackend recognition error: {e}")
            if getattr(self, 'event_bus', None):
                self.event_bus.emit(AudioEvent.RECOGNITION_FAILED, {"error": str(e)})

    def close(self) -> None:
        """Release VRAM by dropping the model."""
        if self._model is not None:
            self._model = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            LOGGER.info("FasterWhisper model unloaded from VRAM.")
