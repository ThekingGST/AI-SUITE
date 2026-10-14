from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from jarvis_ai.utils.helpers import clamp
from jarvis_ai.utils.logger import LOGGER


@dataclass
class VolumeState:
    level: int
    muted: bool


class VolumeController:
    """Real Windows master-volume control through pycaw.

    pycaw endpoints are COM-backed, so this controller creates/uses the endpoint
    inside the calling thread instead of sharing one COM object across threads.
    """

    def __init__(self) -> None:
        self.endpoint_name = "unknown endpoint"
        self._probe_endpoint()

    def _probe_endpoint(self) -> None:
        try:
            endpoint, name = self._create_endpoint()
            self.endpoint_name = name
            level = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            LOGGER.info("Windows volume endpoint initialized: %s at %s percent.", name, level)
        except Exception as exc:
            LOGGER.warning("pycaw volume endpoint unavailable: %s", exc)

    def _create_endpoint(self) -> tuple[Any, str]:
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception as exc:
            LOGGER.debug("COM initialization for volume endpoint skipped: %s", exc)

        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        device = AudioUtilities.GetSpeakers()
        name = str(getattr(device, "FriendlyName", "default speakers"))
        if hasattr(device, "EndpointVolume"):
            return device.EndpointVolume, name
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume), name

    def state(self) -> VolumeState:
        try:
            endpoint, name = self._create_endpoint()
            self.endpoint_name = name
            level = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            muted = bool(endpoint.GetMute())
            LOGGER.info("Current volume: %s percent. Muted: %s. Endpoint: %s", level, muted, name)
            return VolumeState(level=level, muted=muted)
        except Exception as exc:
            LOGGER.exception("Volume state read failed: %s", exc)
            return VolumeState(level=-1, muted=False)

    def set_volume(self, percent: int) -> str:
        target = int(clamp(percent, 0, 100))
        scalar = target / 100.0
        try:
            endpoint, name = self._create_endpoint()
            before = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            LOGGER.info("Current volume: %s percent.", before)
            LOGGER.info("Target volume: %s percent.", target)
            LOGGER.info("Endpoint name: %s", name)
            LOGGER.info("Scalar value applied: %.3f", scalar)
            endpoint.SetMasterVolumeLevelScalar(scalar, None)
            endpoint.SetMute(0, None)
            time.sleep(0.08)
            after = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            muted = bool(endpoint.GetMute())
            LOGGER.info("Read-back volume: %s percent. Muted: %s", after, muted)
            if abs(after - target) <= 2 and not muted:
                return f"Volume set to {after} percent."
            return f"Volume change failed. Requested {target} percent, but Windows reports {after} percent."
        except Exception as exc:
            LOGGER.exception("Volume set failed: %s", exc)
            return f"Volume control failed: {exc}"

    def change_volume(self, delta: int) -> str:
        current = self.state().level
        if current < 0:
            return "Volume control failed: unable to read current Windows volume."
        return self.set_volume(current + delta)

    def mute(self) -> str:
        try:
            endpoint, name = self._create_endpoint()
            LOGGER.info("Endpoint name: %s", name)
            endpoint.SetMute(1, None)
            time.sleep(0.05)
            muted = bool(endpoint.GetMute())
            LOGGER.info("Read-back muted state: %s", muted)
            return "System audio muted." if muted else "Mute command failed. Windows still reports audio unmuted."
        except Exception as exc:
            LOGGER.exception("Mute failed: %s", exc)
            return f"Mute control failed: {exc}"

    def unmute(self) -> str:
        try:
            endpoint, name = self._create_endpoint()
            LOGGER.info("Endpoint name: %s", name)
            endpoint.SetMute(0, None)
            time.sleep(0.05)
            muted = bool(endpoint.GetMute())
            LOGGER.info("Read-back muted state: %s", muted)
            return "System audio unmuted." if not muted else "Unmute command failed. Windows still reports audio muted."
        except Exception as exc:
            LOGGER.exception("Unmute failed: %s", exc)
            return f"Unmute control failed: {exc}"
