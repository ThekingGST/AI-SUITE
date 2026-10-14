from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pyaudio

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.events import AudioEvent, AudioEventBus


@dataclass
class AudioDeviceInfo:
    """Information about an audio input device."""
    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_default: bool


class AudioDeviceManager:
    """Manages audio input hardware devices, enumeration, and hot-plug detection."""

    def __init__(self, event_bus: AudioEventBus) -> None:
        self._event_bus = event_bus
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._devices: Dict[int, AudioDeviceInfo] = {}
        self._active_device_index: Optional[int] = None
        
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
    def start(self) -> None:
        """Initialize PyAudio and start device monitoring."""
        with self._lock:
            if self._pyaudio is None:
                self._pyaudio = pyaudio.PyAudio()
                self._refresh_devices()
                
            if not self._monitor_thread or not self._monitor_thread.is_alive():
                self._stop_event.clear()
                self._monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    name="AudioDeviceMonitor",
                    daemon=True
                )
                self._monitor_thread.start()

    def stop(self) -> None:
        """Stop device monitoring and terminate PyAudio."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
            
        with self._lock:
            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None
                self._devices.clear()
                self._active_device_index = None

    def get_devices(self) -> List[AudioDeviceInfo]:
        """Return a list of all available input devices."""
        with self._lock:
            return list(self._devices.values())

    def get_active_device(self) -> Optional[AudioDeviceInfo]:
        """Return the currently active input device."""
        with self._lock:
            if self._active_device_index is not None:
                return self._devices.get(self._active_device_index)
            # Find default
            for dev in self._devices.values():
                if dev.is_default:
                    return dev
            # Fallback to any input
            if self._devices:
                return next(iter(self._devices.values()))
            return None

    def set_active_device(self, index: int) -> bool:
        """Manually select an input device. Returns True if successful."""
        with self._lock:
            if index in self._devices:
                self._active_device_index = index
                LOGGER.info("AudioDeviceManager: Active device set to '%s' (Index %d)", 
                            self._devices[index].name, index)
                # Emit default device changed
                self._event_bus.emit(AudioEvent.DEFAULT_DEVICE_CHANGED, {
                    "device": self._devices[index]
                })
                return True
            LOGGER.warning("AudioDeviceManager: Attempted to set invalid device index %d", index)
            return False

    def _refresh_devices(self) -> None:
        """Scan PyAudio for devices and update internal state."""
        if not self._pyaudio:
            return
            
        current_devices = {}
        try:
            default_input_info = self._pyaudio.get_default_input_device_info()
            default_index = default_input_info['index']
        except OSError:
            default_index = -1

        try:
            count = self._pyaudio.get_device_count()
            for i in range(count):
                try:
                    info = self._pyaudio.get_device_info_by_index(i)
                    channels = info.get('maxInputChannels', 0)
                    if channels > 0:
                        is_default = (i == default_index)
                        dev = AudioDeviceInfo(
                            index=i,
                            name=info.get('name', 'Unknown'),
                            max_input_channels=channels,
                            default_sample_rate=info.get('defaultSampleRate', 16000.0),
                            is_default=is_default
                        )
                        current_devices[i] = dev
                except OSError:
                    continue
        except Exception as exc:
            LOGGER.error("AudioDeviceManager: Failed to enumerate devices: %s", exc)
            self._event_bus.emit(AudioEvent.DEVICE_ERROR, {"error": str(exc)})
            return

        with self._lock:
            old_indices = set(self._devices.keys())
            new_indices = set(current_devices.keys())

            added = new_indices - old_indices
            removed = old_indices - new_indices

            self._devices = current_devices

            for idx in added:
                LOGGER.info("AudioDeviceManager: Device connected - %s", current_devices[idx].name)
                self._event_bus.emit(AudioEvent.DEVICE_CONNECTED, {"device": current_devices[idx]})

            for idx in removed:
                LOGGER.info("AudioDeviceManager: Device disconnected - index %d", idx)
                self._event_bus.emit(AudioEvent.DEVICE_DISCONNECTED, {"index": idx})
                
                # If active device was removed, reset active device
                if self._active_device_index == idx:
                    self._active_device_index = None
                    new_active = self.get_active_device()
                    if new_active:
                        self._event_bus.emit(AudioEvent.DEFAULT_DEVICE_CHANGED, {"device": new_active})

    def _monitor_loop(self) -> None:
        """Periodically check for device changes."""
        # DISABLED: PyAudio polling in a background thread causes WASAPI stream
        # contention and silences the AudioCaptureWorker stream on Windows.
        # We will only enumerate devices once on startup.
        while not self._stop_event.is_set():
            time.sleep(1)
