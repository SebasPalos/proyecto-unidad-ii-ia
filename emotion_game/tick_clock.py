"""Convierte tiempo real en ticks fijos, para que el puntaje no dependa de los FPS."""

import math

_EPSILON = 1e-9


class TickClock:
    def __init__(self, interval: float, start: float):
        self._interval = interval
        self._start = start
        self._emitted = 0

    def due(self, now: float) -> int:
        """Cuántos ticks nuevos tocan desde la última llamada."""
        elapsed_ticks = math.floor((now - self._start) / self._interval + _EPSILON)
        new_ticks = max(0, elapsed_ticks - self._emitted)
        self._emitted += new_ticks
        return new_ticks
