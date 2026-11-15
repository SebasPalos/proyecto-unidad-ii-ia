"""Efectos de sonido arcade para el puntaje, sintetizados con NumPy (sin archivos de audio).

Sumar puntos: dos notas agudas que suben, tipo "moneda". Restar: un zumbido grave que cae.
El tono cambia un poco con el multiplicador, así una buena racha se oye cada vez más aguda
y una mala cada vez más grave.
"""

import numpy as np
import pygame

SAMPLE_RATE = 22050
LEVELS = 10  # un tono por nivel de multiplicador (x1..x10)
VOLUME_GAIN = 0.20
VOLUME_LOSS = 0.30


def _pulse(freqs: np.ndarray, duty: float, rate: int) -> np.ndarray:
    """Onda de pulso (cuadrada) con frecuencia variable muestra a muestra."""
    phase = np.cumsum(freqs / rate)
    wave = np.where((phase % 1.0) < duty, 1.0, -1.0)
    return wave - wave.mean()  # centrada en cero: sin "golpe" al iniciar ni volumen desperdiciado


def _fade(wave: np.ndarray, rate: int, decay: float) -> np.ndarray:
    n = len(wave)
    envelope = np.exp(-np.arange(n) / (rate * decay))
    edge = max(1, int(rate * 0.004))  # evita "clics" al empezar y al cortar
    envelope[:edge] *= np.linspace(0, 1, edge)
    envelope[-edge:] *= np.linspace(1, 0, edge)
    return wave * envelope


def gain_wave(level: int = 0, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Recompensa: nota corta y luego una cuarta más arriba. ~90 ms."""
    base = 880.0 * 2 ** (level / 12)
    n1, n2 = int(rate * 0.03), int(rate * 0.06)
    freqs = np.concatenate([np.full(n1, base), np.full(n2, base * 4 / 3)])
    wave = _fade(_pulse(freqs, 0.25, rate), rate, decay=0.05)
    return (wave * VOLUME_GAIN * 32767).astype(np.int16)


def loss_wave(level: int = 0, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Penalización: barrido grave hacia abajo con un poco de ruido. ~120 ms."""
    base = 196.0 * 2 ** (-level / 24)
    n = int(rate * 0.12)
    freqs = np.linspace(base, base / 2, n)
    noise = np.random.default_rng(level).uniform(-1, 1, n)
    wave = _fade(_pulse(freqs, 0.5, rate) * 0.8 + noise * 0.2, rate, decay=0.09)
    return (wave * VOLUME_LOSS * 32767).astype(np.int16)


class ScoreSounds:
    """Reproduce el sonido de suma o resta. Si no hay audio, el juego sigue en silencio."""

    def __init__(self):
        self.enabled = False
        self._gain: list[pygame.mixer.Sound] = []
        self._loss: list[pygame.mixer.Sound] = []
        self._channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 256)
            rate, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:
                return
            self._gain = [self._sound(gain_wave(i, rate), channels) for i in range(LEVELS)]
            self._loss = [self._sound(loss_wave(i, rate), channels) for i in range(LEVELS)]
            # Un solo canal: un sonido nuevo corta al anterior en vez de encimarse
            pygame.mixer.set_reserved(1)
            self._channel = pygame.mixer.Channel(0)
            self.enabled = True
        except (pygame.error, NotImplementedError):
            self.enabled = False

    @staticmethod
    def _sound(wave: np.ndarray, channels: int) -> pygame.mixer.Sound:
        if channels > 1:
            wave = np.repeat(wave[:, None], channels, axis=1)
        return pygame.mixer.Sound(buffer=np.ascontiguousarray(wave).tobytes())

    def play_score_change(self, delta: int, multiplier: int = 1) -> str | None:
        """Un sonido por cada cambio real del puntaje. Devuelve cuál sonó."""
        if delta == 0:
            return None
        kind = "gain" if delta > 0 else "loss"
        if self.enabled:
            level = max(0, min(LEVELS - 1, multiplier - 1))
            self._channel.play((self._gain if delta > 0 else self._loss)[level])
        return kind
