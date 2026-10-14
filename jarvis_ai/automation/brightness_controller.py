from __future__ import annotations

from utils.helpers import clamp
from utils.logger import LOGGER


class BrightnessController:
    """Multi-monitor safe brightness control using screen_brightness_control."""

    def monitors(self) -> list[str]:
        try:
            import screen_brightness_control as sbc

            monitors = sbc.list_monitors()
            LOGGER.info("Brightness monitors detected: %s", monitors)
            return [str(monitor) for monitor in monitors]
        except Exception as exc:
            LOGGER.warning("Brightness monitor detection failed: %s", exc)
            return []

    def get_brightness(self) -> int | None:
        try:
            import screen_brightness_control as sbc

            self.monitors()
            values = sbc.get_brightness()
            LOGGER.info("Brightness read values: %s", values)
            if isinstance(values, list) and values:
                return int(sum(values) / len(values))
            if isinstance(values, int):
                return values
        except Exception as exc:
            LOGGER.warning("Brightness read failed: %s", exc)
        return None

    def set_brightness(self, percent: int) -> str:
        percent = int(clamp(percent, 0, 100))
        try:
            import screen_brightness_control as sbc

            monitors = self.monitors()
            if not monitors:
                return "Brightness control is not available: no supported brightness monitors were detected."
            before = self.get_brightness()
            LOGGER.info("Current brightness: %s", before)
            LOGGER.info("Target brightness: %s", percent)
            sbc.set_brightness(percent)
            after = self.get_brightness()
            LOGGER.info("Read-back brightness: %s", after)
            if after is not None and abs(after - percent) <= 3:
                return f"Brightness set to {after} percent."
            return f"Brightness change failed. Requested {percent} percent, but display reports {after}."
        except Exception as exc:
            LOGGER.exception("Brightness control failed: %s", exc)
            return f"Brightness control is not available: {exc}"

    def change_brightness(self, delta: int) -> str:
        current = self.get_brightness()
        if current is None:
            return "Brightness control is not available on this display."
        return self.set_brightness(current + delta)
