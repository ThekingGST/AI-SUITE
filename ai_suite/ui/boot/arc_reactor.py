"""AI Suite Boot Screen — Arc Reactor layered rendering engine.

The reactor is composed of independent rendering layers, each with its own
``update(dt)`` and ``draw(painter, cx, cy, base_radius)`` methods.  The
ArcReactor widget simply orchestrates these layers and drives the 60 fps
paint timer.

All dimensions are derived from the widget size via a base_radius computed
as ``min(width, height) * REACTOR_SCALE`` — making the renderer fully
resolution-independent.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import List

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QRadialGradient, QBrush, QPainterPath,
)
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtProperty

from ai_suite.ui.boot.boot_theme import (
    CYAN_PRIMARY, CYAN_DIM, CYAN_GLOW, WHITE_CORE, BG_COLOR,
    REACTOR_SCALE, FRAME_INTERVAL_MS, STAGE_ANIM_DURATION_MS,
)
from ai_suite.ui.boot.particles import ParticleSystem


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Abstract Layer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ReactorLayer(ABC):
    """Base class for each visual layer of the reactor."""

    def __init__(self):
        self._opacity: float = 0.0     # 0 = invisible, 1 = fully visible

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = max(0.0, min(1.0, value))

    @abstractmethod
    def update(self, dt: float):
        """Advance internal state by *dt* seconds."""

    @abstractmethod
    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        """Render this layer.  *cx, cy* is the center; *base_r* is the
        outer reference radius.  All sub-radii should be fractions of
        *base_r*."""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Glow / Halo Layer (drawn first — behind everything)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GlowLayer(ReactorLayer):
    """Soft radial bloom extending past the outer ring."""

    def __init__(self):
        super().__init__()
        self._radius_factor = 1.6   # glow extends to 1.6× base_r

    def update(self, dt: float):
        pass  # Static glow — intensity driven by opacity alone.

    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        if self._opacity < 0.01:
            return
        r = base_r * self._radius_factor
        grad = QRadialGradient(cx, cy, r)
        c = CYAN_PRIMARY
        alpha = int(CYAN_GLOW.alpha() * self._opacity)
        grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), int(60 * self._opacity)))
        grad.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(), alpha))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core Layer (center bright dot)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CoreLayer(ReactorLayer):
    """Pulsing center circle with radial gradient (white → cyan)."""

    def __init__(self):
        super().__init__()
        self._pulse_phase: float = 0.0   # radians
        self._pulse_speed: float = 2.5   # rad/s

    @property
    def pulse_value(self) -> float:
        """0-1 sinusoidal pulse."""
        return 0.5 + 0.5 * math.sin(self._pulse_phase)

    def update(self, dt: float):
        self._pulse_phase += self._pulse_speed * dt

    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        if self._opacity < 0.01:
            return
        # Core radius oscillates between 0.08 and 0.12 of base_r
        min_r = base_r * 0.08
        max_r = base_r * 0.14
        r = min_r + (max_r - min_r) * self.pulse_value

        grad = QRadialGradient(cx, cy, r)
        a = int(255 * self._opacity)
        grad.setColorAt(0.0, QColor(220, 245, 255, a))
        grad.setColorAt(0.4, QColor(0, 212, 255, a))
        grad.setColorAt(1.0, QColor(0, 212, 255, 0))

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ring Layers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RingLayer(ReactorLayer):
    """A single rotating ring rendered as arc segments."""

    def __init__(
        self,
        radius_frac: float,          # fraction of base_r
        width_frac: float,           # pen width as fraction of base_r
        rotation_speed: float,       # degrees per second (negative = CCW)
        segments: int = 0,           # 0 = continuous arc, >0 = segmented
        dash_pattern: list | None = None,
        color: QColor | None = None,
    ):
        super().__init__()
        self._radius_frac = radius_frac
        self._width_frac = width_frac
        self._rotation_speed = rotation_speed
        self._segments = segments
        self._dash_pattern = dash_pattern
        self._color = color or CYAN_PRIMARY
        self._angle: float = 0.0     # current rotation in degrees

    def update(self, dt: float):
        self._angle += self._rotation_speed * dt
        self._angle %= 360.0

    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        if self._opacity < 0.01:
            return

        r = base_r * self._radius_frac
        w = max(1.0, base_r * self._width_frac)

        pen_color = QColor(self._color)
        pen_color.setAlpha(int(pen_color.alpha() * self._opacity))
        pen = QPen(pen_color, w)
        pen.setCapStyle(Qt.FlatCap)
        if self._dash_pattern:
            pen.setDashPattern(self._dash_pattern)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        painter.translate(-cx, -cy)

        if self._segments > 0:
            # Draw segmented arcs with equal gaps
            span = 360.0 / self._segments
            gap = span * 0.2  # 20% gap
            arc_span = span - gap
            for i in range(self._segments):
                start = i * span
                painter.drawArc(rect, int(start * 16), int(arc_span * 16))
        else:
            painter.drawEllipse(rect)

        painter.restore()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tick Layer (small marks on the outer ring)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TickLayer(ReactorLayer):
    """Small radial tick marks evenly spaced around a ring."""

    def __init__(
        self,
        radius_frac: float,
        tick_count: int = 36,
        tick_length_frac: float = 0.04,
        rotation_speed: float = 0.0,
        color: QColor | None = None,
    ):
        super().__init__()
        self._radius_frac = radius_frac
        self._tick_count = tick_count
        self._tick_length_frac = tick_length_frac
        self._rotation_speed = rotation_speed
        self._color = color or CYAN_DIM
        self._angle: float = 0.0

    def update(self, dt: float):
        self._angle += self._rotation_speed * dt

    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        if self._opacity < 0.01:
            return

        r_inner = base_r * self._radius_frac
        r_outer = r_inner + base_r * self._tick_length_frac
        w = max(1.0, base_r * 0.008)

        pen_color = QColor(self._color)
        pen_color.setAlpha(int(pen_color.alpha() * self._opacity))
        pen = QPen(pen_color, w)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)

        step = 360.0 / self._tick_count
        for i in range(self._tick_count):
            angle_rad = math.radians(i * step + self._angle)
            x1 = cx + r_inner * math.cos(angle_rad)
            y1 = cy + r_inner * math.sin(angle_rad)
            x2 = cx + r_outer * math.cos(angle_rad)
            y2 = cy + r_outer * math.sin(angle_rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ArcReactor Widget
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ArcReactor(QWidget):
    """The visual centerpiece of the boot screen.

    Composes multiple :class:`ReactorLayer` instances and drives them
    with a 60 fps paint timer.  All sizing is resolution-independent,
    derived from ``min(width, height) * REACTOR_SCALE``.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # ── Build layers (order = back-to-front drawing order) ──
        self._glow = GlowLayer()
        self._core = CoreLayer()

        self._inner_ring = RingLayer(
            radius_frac=0.30,
            width_frac=0.010,
            rotation_speed=30.0,         # 30 deg/s clockwise
            dash_pattern=[4, 6],
            color=CYAN_DIM,
        )
        self._middle_ring = RingLayer(
            radius_frac=0.55,
            width_frac=0.018,
            rotation_speed=-15.0,        # 15 deg/s counter-clockwise
            segments=4,
            color=CYAN_PRIMARY,
        )
        self._outer_ring = RingLayer(
            radius_frac=0.80,
            width_frac=0.008,
            rotation_speed=8.0,          # 8 deg/s clockwise
            color=CYAN_DIM,
        )
        self._ticks = TickLayer(
            radius_frac=0.82,
            tick_count=60,
            tick_length_frac=0.035,
            rotation_speed=8.0,          # moves with outer ring
            color=CYAN_DIM,
        )

        # ── Particle system ──────────────────────────────────────
        self._particles = ParticleSystem()

        # Ordered back → front
        self._layers: List[ReactorLayer] = [
            self._glow,
            self._outer_ring,
            self._ticks,
            self._middle_ring,
            self._inner_ring,
            self._core,
        ]

        # ── Reactor level (0-8) drives which layers are visible ──
        self._reactor_level: int = 0

        # ── Smooth opacity targets (for interpolation) ──────────
        self._opacity_targets: dict = {}   # layer → target opacity
        self._lerp_speed = 1000.0 / STAGE_ANIM_DURATION_MS  # units per second

        # ── 60 fps timer ────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(FRAME_INTERVAL_MS)

    # ── Reactor level property ──────────────────────────────────

    def get_reactor_level(self) -> int:
        return self._reactor_level

    def set_reactor_level(self, level: int):
        """Set which layers are active.  Each level fades in one more
        visual element.  See boot_theme.STAGE_CONFIG for the mapping."""
        self._reactor_level = level
        self._apply_level()

    reactor_level_prop = pyqtProperty(int, get_reactor_level, set_reactor_level)

    def _apply_level(self):
        """Map reactor_level → layer opacity targets.

        Level 0: everything dark
        Level 1: core glows
        Level 2: inner ring
        Level 3: middle ring
        Level 4: outer ring + ticks
        Level 5: particles activate
        Level 6: glow intensifies
        Level 7: full brightness
        Level 8: final pulse (handled externally)
        Level 9: final dissolve (rings and core fade to 0, bloom expands)
        """
        lvl = self._reactor_level

        # Set targets — _tick() will smoothly interpolate toward these.
        if lvl == 9:
            self._opacity_targets[id(self._core)]        = 0.0
            self._opacity_targets[id(self._inner_ring)]  = 0.0
            self._opacity_targets[id(self._middle_ring)] = 0.0
            self._opacity_targets[id(self._outer_ring)]  = 0.0
            self._opacity_targets[id(self._ticks)]       = 0.0
            self._opacity_targets[id(self._glow)]        = 1.0
            self._particle_target = 0.0
            return

        self._opacity_targets[id(self._core)]        = 1.0 if lvl >= 1 else 0.0
        self._opacity_targets[id(self._inner_ring)]  = 1.0 if lvl >= 2 else 0.0
        self._opacity_targets[id(self._middle_ring)] = 1.0 if lvl >= 3 else 0.0
        self._opacity_targets[id(self._outer_ring)]  = 1.0 if lvl >= 4 else 0.0
        self._opacity_targets[id(self._ticks)]       = 1.0 if lvl >= 4 else 0.0
        self._opacity_targets[id(self._glow)]        = min(1.0, 0.3 + 0.1 * max(0, lvl - 5))

        # Particle target
        self._particle_target = 1.0 if lvl >= 5 else 0.0

    # ── Frame tick ──────────────────────────────────────────────

    def _tick(self):
        if not self.isVisible():
            return
        
        dt = FRAME_INTERVAL_MS / 1000.0

        # Smooth opacity interpolation toward targets
        step = self._lerp_speed * dt
        for layer in self._layers:
            layer.update(dt)
            target = self._opacity_targets.get(id(layer), layer.opacity)
            if layer.opacity < target:
                layer.opacity = min(target, layer.opacity + step)
            elif layer.opacity > target:
                layer.opacity = max(target, layer.opacity - step)

        # Particle opacity interpolation
        p_target = getattr(self, '_particle_target', 0.0)
        p_cur = self._particles.active_opacity
        if p_cur < p_target:
            self._particles.active_opacity = min(p_target, p_cur + step)
        elif p_cur > p_target:
            self._particles.active_opacity = max(p_target, p_cur - step)
        self._particles.tick(dt)

        self.update()  # schedule repaint

    # ── Paint ───────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        base_r = min(w, h) * REACTOR_SCALE

        for layer in self._layers:
            layer.draw(painter, cx, cy, base_r)

        # Particles drawn on top of rings but below any future overlay
        self._particles.draw(painter, cx, cy, base_r)

        painter.end()
