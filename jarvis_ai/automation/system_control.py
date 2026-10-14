from __future__ import annotations

import ctypes
import os
import subprocess
from dataclasses import dataclass

import psutil
import pyautogui

from jarvis_ai.utils.helpers import clamp, is_windows
from jarvis_ai.utils.logger import LOGGER


@dataclass
class SystemStatus:
    cpu: float
    ram: float
    battery: str
    wifi: str


class SystemControl:
    def status(self) -> SystemStatus:
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return SystemStatus(0.0, 0.0, "unavailable", "unavailable")
            
        cpu = intel.inspect("cpu").metrics.get("usage_percent", 0.0)
        ram = intel.inspect("memory").metrics.get("usage_percent", 0.0)
        bat_report = intel.inspect("battery")
        net_report = intel.inspect("network")
        
        return SystemStatus(
            cpu=cpu,
            ram=ram,
            battery=bat_report.summary,
            wifi=net_report.summary
        )

    def lock(self) -> str:
        if is_windows():
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked."
        return "Lock workstation is optimized for Windows."

    def shutdown(self) -> str:
        subprocess.Popen(["shutdown", "/s", "/t", "5"], shell=False, creationflags=0x08000000)
        return "Shutdown scheduled in five seconds."

    def restart(self) -> str:
        subprocess.Popen(["shutdown", "/r", "/t", "5"], shell=False, creationflags=0x08000000)
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
        try:
            image = pyautogui.screenshot()
        except Exception as exc:
            LOGGER.warning("Screenshot failed: %s", exc)
            return "I could not take a screenshot."
        
        if not path:
            from jarvis_ai.config import SCREENSHOT_DIR
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
                check=False,
                creationflags=0x08000000,
            )
            return f"Brightness set to {percent}%."
        except Exception as exc:
            LOGGER.warning("Brightness control failed: %s", exc)
            return "Brightness control is not available on this display."


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
