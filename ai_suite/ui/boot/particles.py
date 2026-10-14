"""AI Suite Boot Screen — Lightweight particle system.

Particles orbit around the Arc Reactor at varying radii and speeds,
creating an organic, living feel.  All dimensions are relative to a
``base_radius`` passed at draw time, making the system fully
resolution-independent.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QBrush
from PyQt5.QtCore import Qt, QRectF

from ai_suite.ui.boot.boot_theme import CYAN_PRIMARY, PARTICLE_COUNT


@dataclass
class Particle:
    """A single orbiting particle."""
    angle: float            # current angle in radians
    radius_frac: float      # orbit radius as fraction of base_r (0.85–1.1)
    speed: float            # radians per second
    size_frac: float        # dot size as fraction of base_r
    base_opacity: float     # max opacity (0-1)


class ParticleSystem:
    """Manages a swarm of orbiting particles around the reactor."""

    def __init__(self, count: int = PARTICLE_COUNT):
        self._particles: list[Particle] = []
        self._active_opacity: float = 0.0   # global fade (0 = invisible)

        rng = random.Random(42)  # deterministic for consistency
        for _ in range(count):
            self._particles.append(Particle(
                angle=rng.uniform(0, 2 * math.pi),
                radius_frac=rng.uniform(0.88, 1.12),
                speed=rng.uniform(0.3, 0.8) * rng.choice([1, -1]),
                size_frac=rng.uniform(0.012, 0.025),
                base_opacity=rng.uniform(0.3, 0.8),
            ))

    @property
    def active_opacity(self) -> float:
        return self._active_opacity

    @active_opacity.setter
    def active_opacity(self, value: float):
        self._active_opacity = max(0.0, min(1.0, value))

    def tick(self, dt: float):
        """Advance all particle positions by *dt* seconds."""
        for p in self._particles:
            p.angle += p.speed * dt

    def draw(self, painter: QPainter, cx: float, cy: float, base_r: float):
        """Render all particles as small glowing dots."""
        if self._active_opacity < 0.01:
            return

        painter.setPen(Qt.NoPen)

        for p in self._particles:
            r = base_r * p.radius_frac
            x = cx + r * math.cos(p.angle)
            y = cy + r * math.sin(p.angle)

            dot_r = base_r * p.size_frac
            alpha = int(255 * p.base_opacity * self._active_opacity)

            grad = QRadialGradient(x, y, dot_r)
            grad.setColorAt(0.0, QColor(0, 212, 255, alpha))
            grad.setColorAt(1.0, QColor(0, 212, 255, 0))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QRectF(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2))
