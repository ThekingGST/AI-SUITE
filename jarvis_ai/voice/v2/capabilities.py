from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class BackendCapabilities:
    """Capabilities exposed by a TTS Backend.
    
    Used by the Voice Framework to intelligently route speech requests.
    """
    
    supports_streaming: bool = False
    supports_interrupt: bool = False
    
    # Audio formatting
    supports_ssml: bool = False
    
    # Tuning
    supports_pitch: bool = False
    supports_rate: bool = False
    supports_volume: bool = False
    supports_voice_selection: bool = False
    
    # Output types
    supports_stream_output: bool = False
    supports_file_output: bool = False
    
    # Environment requirements
    offline: bool = False
    network_required: bool = True


@dataclass
class BackendHealth:
    """Runtime health status of a TTS Backend."""
    
    is_available: bool = False
    is_online: bool = False
    
    last_error: str | None = None
    last_error_time: float = 0.0
    last_success_time: float = 0.0
    
    # Running average latency in ms (TTFB)
    latency_ms: float = 0.0
    
    def record_success(self, latency: float = 0.0) -> None:
        self.is_available = True
        self.is_online = True
        self.last_success_time = time.time()
        self.last_error = None
        if latency > 0:
            if self.latency_ms == 0:
                self.latency_ms = latency
            else:
                # Exponential moving average
                self.latency_ms = (self.latency_ms * 0.8) + (latency * 0.2)
                
    def record_error(self, error: str, is_network_error: bool = False) -> None:
        self.last_error = error
        self.last_error_time = time.time()
        if is_network_error:
            self.is_online = False
            self.is_available = False
        
    def reset(self) -> None:
        self.is_available = True
        self.is_online = True
        self.last_error = None
