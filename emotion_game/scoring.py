"""Reglas del puntaje. Lógica pura: no sabe nada de cámaras, modelos ni Pygame."""

from dataclasses import dataclass

from emotion_game import config

POSITIVE = 1
NEGATIVE = -1


@dataclass(frozen=True)
class Observation:
    """Lo que el modelo vio en un tick. label=None significa que no detectó rostro."""

    label: str | None
    conf: float


class ScoreKeeper:
    def __init__(
        self,
        target: str,
        round_ticks: int = config.ROUND_TICKS,
        multiplier_step: int = config.MULTIPLIER_STEP_TICKS,
        debounce_ticks: int = config.DEBOUNCE_TICKS,
        no_detection_penalty: int = config.NO_DETECTION_PENALTY,
        tick_seconds: float = config.TICK_SECONDS,
    ):
        self.target = target
        self._round_ticks = round_ticks
        self._multiplier_step = multiplier_step
        self._debounce_ticks = debounce_ticks
        self._no_detection_penalty = no_detection_penalty
        self._tick_seconds = tick_seconds

        self.score = 0
        self.ticks = 0
        self.best_conf = 0.0
        self.target_ticks = 0
        self.last_delta = 0

        self._state = None  # POSITIVE, NEGATIVE o None antes del primer tick
        self._streak = 0  # ticks seguidos puntuados en el estado actual
        self._pending = 0  # ticks seguidos en el estado contrario (debounce)

    @property
    def finished(self) -> bool:
        return self.ticks >= self._round_ticks

    @property
    def remaining_seconds(self) -> float:
        return max(0, self._round_ticks - self.ticks) * self._tick_seconds

    @property
    def multiplier(self) -> int:
        return 1 + max(0, self._streak - 1) // self._multiplier_step

    @property
    def state(self):
        return self._state

    @property
    def is_pending(self) -> bool:
        return self._pending > 0

    def tick(self, obs: Observation) -> int:
        """Aplica un tick y devuelve los puntos que sumó o restó."""
        if self.finished:
            return 0
        self.ticks += 1

        if obs.label == self.target:
            self.target_ticks += 1
            self.best_conf = max(self.best_conf, obs.conf)

        polarity = POSITIVE if obs.label == self.target else NEGATIVE

        if self._state is None:
            self._state = polarity
        elif polarity != self._state:
            self._pending += 1
            if self._pending < self._debounce_ticks:
                self.last_delta = 0
                return 0
            self._state = polarity
            self._streak = 0
        self._pending = 0

        self._streak += 1
        delta = self._points(obs) * self.multiplier * self._state
        self.score += delta
        self.last_delta = delta
        return delta

    def _points(self, obs: Observation) -> int:
        if obs.label is None:
            return self._no_detection_penalty
        return int(obs.conf * 100)
