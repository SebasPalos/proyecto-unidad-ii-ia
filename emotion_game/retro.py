"""Estética arcade retro: paleta neón, caras en pixel art, fuente pixelada y efectos CRT.

Solo dibuja; no sabe nada de reglas del juego, cámaras ni modelos.
"""

import math
import random

import pygame

# Paleta (la misma de la lona)
BG = (13, 2, 33)
BG2 = (26, 6, 56)
PINK = (255, 42, 109)
CYAN = (5, 217, 232)
YELLOW = (255, 225, 77)
GREEN = (57, 255, 106)
ORANGE = (255, 159, 28)
LAVENDER = (184, 166, 255)
WHITE = (244, 241, 255)
MUTED = (140, 120, 190)
DIM = (40, 22, 80)

EMOTION_COLORS = {
    "Happy": YELLOW,
    "Sad": CYAN,
    "Angry": PINK,
    "Surprise": ORANGE,
    "Disgust": GREEN,
    "Natural": LAVENDER,
}

# ------------------------------------------------------------------ caras

FACE_SIZE = 16
# K = contorno, Y = relleno
BASE_FACE = (
    ".....KKKKKK.....",
    "...KKYYYYYYKK...",
    "..KYYYYYYYYYYK..",
    ".KYYYYYYYYYYYYK.",
    ".KYYYYYYYYYYYYK.",
    "KYYYYYYYYYYYYYYK",
    "KYYYYYYYYYYYYYYK",
    "KYYYYYYYYYYYYYYK",
    "KYYYYYYYYYYYYYYK",
    "KYYYYYYYYYYYYYYK",
    "KYYYYYYYYYYYYYYK",
    ".KYYYYYYYYYYYYK.",
    ".KYYYYYYYYYYYYK.",
    "..KYYYYYYYYYYK..",
    "...KKYYYYYYKK...",
    ".....KKKKKK.....",
)


def _row(x0: int, x1: int, y: int) -> list[tuple[int, int]]:
    return [(x, y) for x in range(x0, x1 + 1)]


_EYES = [(5, 5), (6, 5), (5, 6), (6, 6), (9, 5), (10, 5), (9, 6), (10, 6)]

# Rasgos (x, y) de cada emoción, en la misma cuadrícula de 16 x 16
FEATURES = {
    "Happy": _EYES + [(3, 9), (12, 9), (4, 10), (11, 10)] + _row(5, 10, 11),
    "Sad": _EYES + _row(5, 10, 10) + [(4, 11), (11, 11), (3, 12), (12, 12)],
    "Angry": [(4, 3), (5, 4), (6, 4), (11, 3), (10, 4), (9, 4), (5, 6), (6, 6), (9, 6), (10, 6)]
    + _row(5, 10, 10) + [(4, 11), (11, 11)],
    "Surprise": [(5, 4), (6, 4), (5, 5), (6, 5), (9, 4), (10, 4), (9, 5), (10, 5),
                 (7, 8), (8, 8), (6, 9), (9, 9), (6, 10), (9, 10), (6, 11), (9, 11), (7, 12), (8, 12)],
    "Disgust": _row(4, 6, 6) + _row(9, 11, 6)
    + [(4, 11), (5, 10), (6, 10), (7, 11), (8, 11), (9, 10), (10, 10), (11, 11)],
    "Natural": _EYES + _row(5, 10, 10),
}


def face_grid(label: str) -> list[str]:
    """Cara de la emoción: K contorno, Y relleno, F rasgos, '.' vacío."""
    features = set(FEATURES.get(label, FEATURES["Natural"]))
    return [
        "".join("F" if (x, y) in features else ch for x, ch in enumerate(row))
        for y, row in enumerate(BASE_FACE)
    ]


def face_surface(label: str, cell: int, filled: bool = False) -> pygame.Surface:
    """filled=False: icono de contorno neón. filled=True: cara rellena estilo 'jugador'."""
    color = EMOTION_COLORS.get(label, LAVENDER)
    palette = (
        {"K": WHITE, "Y": color, "F": BG} if filled else {"K": color, "Y": BG, "F": color}
    )
    surface = pygame.Surface((FACE_SIZE * cell, FACE_SIZE * cell), pygame.SRCALPHA)
    for y, row in enumerate(face_grid(label)):
        for x, ch in enumerate(row):
            if ch in palette:
                surface.fill(palette[ch], (x * cell, y * cell, cell, cell))
    if filled:  # brillo
        for x, y in ((4, 3), (3, 4)):
            surface.fill((255, 247, 194), (x * cell, y * cell, cell, cell))
    return surface


# ------------------------------------------------------------------ fuente

_FONT_NAMES = "consolas,lucidaconsole,couriernew,monospace"
# Por debajo de 12 px las fuentes del sistema se deforman (la M se vuelve N)
_MIN_BASE = 12


class PixelFont:
    """Texto pixelado: se dibuja chico y sin suavizado, y se agranda en píxeles enteros."""

    def __init__(self, size: int):
        if size <= 32:
            self.scale = 2
        elif size <= 64:
            self.scale = 3
        else:
            self.scale = max(4, size // 24)
        base = max(_MIN_BASE, round(size / self.scale))
        self._font = pygame.font.SysFont(_FONT_NAMES, base, bold=True)

    def render(self, text: str, color) -> pygame.Surface:
        small = self._font.render(text, False, color)
        clean = pygame.Surface(small.get_size(), pygame.SRCALPHA)
        clean.blit(small, (0, 0))
        w, h = clean.get_size()
        return pygame.transform.scale(clean, (w * self.scale, h * self.scale))


# ------------------------------------------------------------------ efectos


def scanlines(size: tuple[int, int], gap: int = 3, alpha: int = 60) -> pygame.Surface:
    """Líneas oscuras horizontales, como en una pantalla CRT."""
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(0, size[1], gap):
        surface.fill((0, 0, 0, alpha), (0, y, size[0], 1))
    return surface


def starfield(area: pygame.Rect, count: int, seed: int) -> list[tuple[int, int, int, tuple]]:
    """Estrellas fijas (x, y, tamaño, color). Misma semilla, mismo cielo."""
    rng = random.Random(seed)
    stars = []
    for _ in range(count):
        x = rng.randrange(area.left, area.right)
        y = rng.randrange(area.top, area.bottom)
        size = 4 if rng.random() < 0.2 else 2
        color = CYAN if rng.random() < 0.3 else WHITE
        stars.append((x, y, size, color))
    return stars


def segments_lit(fraction: float, segments: int) -> int:
    """Cuántos bloques de una barra segmentada se encienden. Cualquier avance enciende uno."""
    fraction = max(0.0, min(1.0, fraction))
    # round() evita que 0.3 * 10 = 3.0000000004 encienda un bloque de más
    return math.ceil(round(fraction * segments, 6))


def blink(t: float, period: float = 1.0) -> bool:
    """Encendido la primera mitad de cada periodo: para textos que parpadean."""
    return (t % period) < period / 2
