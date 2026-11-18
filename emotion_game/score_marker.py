"""Marcador flotante del puntaje: formato, animación y posición sobre la cabeza.

Lógica pura. No calcula puntos (eso es de scoring.py): solo observa el puntaje real
cuadro a cuadro, avisa cuándo cambió y lleva los tiempos de la animación. El marcador
flotante y el panel lateral leen el MISMO valor de aquí, por eso nunca se desfasan.
"""

from dataclasses import dataclass

import pygame

ROLL_SECONDS = 0.08  # lo que tardan los dígitos en "rodar" al nuevo valor (< 1 tick)
FLASH_SECONDS = 0.24  # destello verde / rojo tras cada cambio
POPUP_SECONDS = 0.6  # vida de los "+80" / "-100" que salen volando
MAX_POPUPS = 4


def format_score(score: int) -> str:
    """Siempre con signo y mínimo tres dígitos: +000, +080, -100, +1,250."""
    sign = "-" if score < 0 else "+"
    return f"{sign}{abs(score):03,d}"


def format_multiplier(multiplier: int, pending: bool = False) -> str:
    return f"x{multiplier}.." if pending else f"x{multiplier}"


@dataclass(frozen=True)
class Popup:
    delta: int
    born: float
    seq: int  # número de cambio; sirve para repartirlos en columnas y que no se encimen


class ScoreFx:
    """Sigue al puntaje real y anima sus cambios."""

    def __init__(self, score: int = 0, now: float = 0.0):
        self.reset(score, now)

    def reset(self, score: int = 0, now: float = 0.0) -> None:
        self._target = score
        self._from = score
        self._changed_at = now - 10.0  # sin destello al empezar
        self.direction = 0  # +1 subió, -1 bajó, 0 aún no cambia
        self.popups: list[Popup] = []
        self._seq = 0

    def update(self, score: int, now: float) -> int:
        """Se llama una vez por cuadro con el puntaje real.

        Devuelve cuánto cambió desde la llamada anterior; 0 si sigue igual. Ese valor es
        el único disparador de sonidos y animaciones: un cambio = un evento, aunque en el
        cuadro hayan caído varios ticks o la cámara haya dado muchos cuadros sin cambio.
        """
        delta = score - self._target
        if delta == 0:
            return 0
        self._from = self.shown(now)
        self._target = score
        self._changed_at = now
        self.direction = 1 if delta > 0 else -1
        self.popups = [p for p in self.popups if now - p.born < POPUP_SECONDS]
        self._seq += 1
        self.popups = (self.popups + [Popup(delta, now, self._seq)])[-MAX_POPUPS:]
        return delta

    def shown(self, now: float) -> int:
        """Valor que se dibuja: rueda del anterior al real y se queda en el real."""
        t = (now - self._changed_at) / ROLL_SECONDS
        if t >= 1:
            return self._target
        t = max(0.0, t)
        return round(self._from + (self._target - self._from) * t)

    def flash(self, now: float) -> float:
        """Intensidad del destello: 1 justo al cambiar, baja a 0."""
        t = (now - self._changed_at) / FLASH_SECONDS
        if t < 0 or t >= 1:
            return 0.0
        return (1 - t) ** 2

    def live_popups(self, now: float) -> list[tuple[int, int, float]]:
        """(delta, número de cambio, avance 0..1) de los puntos que siguen volando."""
        return [
            (p.delta, p.seq, (now - p.born) / POPUP_SECONDS)
            for p in self.popups
            if 0 <= now - p.born < POPUP_SECONDS
        ]


def place_marker(size: tuple[int, int], face: pygame.Rect, tag: pygame.Rect,
                 bounds: pygame.Rect, gap: int = 10) -> pygame.Rect:
    """Dónde va el marcador: arriba de la cabeza y a la derecha de la etiqueta de emoción.

    Si ahí no cabe (rostro pegado a un borde), prueba otros lugares que tampoco tapen
    la cara ni la etiqueta.
    """
    w, h = size
    side_top = max(bounds.top, min(face.top, bounds.bottom - h))
    candidates = [
        pygame.Rect(tag.right + gap, face.top - gap - h, w, h),  # derecha de la etiqueta
        pygame.Rect(max(bounds.left, min(tag.left, bounds.right - w)), tag.top - gap - h, w, h),
        pygame.Rect(face.right + gap, side_top, w, h),  # a un lado de la cara
        pygame.Rect(face.left - gap - w, side_top, w, h),
    ]
    for rect in candidates:
        if bounds.contains(rect) and not rect.colliderect(face) and not rect.colliderect(tag):
            return rect
    return candidates[0].clamp(bounds)
