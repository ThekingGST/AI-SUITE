from __future__ import annotations

import ctypes
import os
import subprocess
from dataclasses import dataclass

import psutil
import pyautogui

from utils.helpers import clamp, is_windows
from utils.logger import LOGGER


@dataclass
class SystemStatus:
    cpu: float
    ram: float
    battery: str
    wifi: str


class SystemControl:
    def status(self) -> SystemStatus:
        battery = psutil.sensors_battery()
        battery_text = "Battery unavailable"
        if battery:
            plugged = "charging" if battery.power_plugged else "on battery"
            battery_text = f"{battery.percent:.0f}% {plugged}"
        return SystemStatus(
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
            battery=battery_text,
            wifi=self._wifi_status(),
        )

    def lock(self) -> str:
        if is_windows():
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked."
        return "Lock workstation is optimized for Windows."

    def shutdown(self) -> str:
        subprocess.Popen(["shutdown", "/s", "/t", "5"], shell=False)
        return "Shutdown scheduled in five seconds."

    def restart(self) -> str:
        subprocess.Popen(["shutdown", "/r", "/t", "5"], shell=False)
        return "Restart scheduled in five seconds."

    def set_volume_relative(self, direction: str, steps: int = 5) -> str:
        key = "volumeup" if direction == "up" else "volumedown"
        for _ in range(max(1, steps)):
            pyautogui.press(key)
        return f"Volume {direction}."

    def mute(self) -> str:
        pyautogui.press("volumemute")
        return "Audio mute toggled."

    def screenshot(self, path: str | None = None) -> str:
        image = pyautogui.screenshot()
        if not path:
            from config import SCREENSHOT_DIR
            from utils.helpers import timestamp_slug

            path = str(SCREENSHOT_DIR / f"screenshot_{timestamp_slug()}.png")
        image.save(path)
        return path

    def brightness(self, percent: int) -> str:
        percent = int(clamp(percent, 0, 100))
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{percent})",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return f"Brightness set to {percent}%."
        except Exception as exc:
            LOGGER.warning("Brightness control failed: %s", exc)
            return "Brightness control is not available on this display."

    @staticmethod
    def _wifi_status() -> str:
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            output = result.stdout.lower()
            if "state" in output and "connected" in output:
                return "connected"
            return "disconnected"
        except Exception:
            return "unknown"


def close_process_by_name(name: str) -> str:
    target = name.lower().replace(".exe", "")
    killed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            proc_name = (proc.info.get("name") or "").lower().replace(".exe", "")
            if target in proc_name:
                proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return f"Closed {killed} process matching {name}." if killed else f"No process found for {name}."
