"""Detectores de emociones. El juego solo conoce la interfaz detect(frame) -> Detection | None."""

from dataclasses import dataclass
from pathlib import Path

from emotion_game import config


@dataclass(frozen=True)
class Detection:
    label: str
    conf: float
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 en píxeles


def pick_player(detections: list[Detection]) -> Detection | None:
    """El jugador es el rostro más grande: el que está más cerca de la cámara."""
    if not detections:
        return None
    return max(detections, key=lambda d: (d.box[2] - d.box[0]) * (d.box[3] - d.box[1]))


class YoloDetector:
    def __init__(self, model_path: Path = config.MODEL_PATH, conf: float = config.DETECTION_CONF):
        from ultralytics import YOLO  # import tardío: el modo de prueba no necesita ultralytics

        self._model = YOLO(str(model_path))
        self._conf = conf

    @property
    def class_names(self) -> list[str]:
        return list(self._model.names.values())

    def detect(self, frame) -> Detection | None:
        result = self._model.predict(frame, conf=self._conf, verbose=False)[0]
        detections = [
            Detection(
                label=self._model.names[int(box.cls)],
                conf=float(box.conf),
                box=tuple(int(v) for v in box.xyxy[0].tolist()),
            )
            for box in result.boxes
        ]
        return pick_player(detections)


class FakeDetector:
    """Simula al modelo con el teclado, para probar el juego sin best.pt."""

    def __init__(self, conf: float = 0.8, box: tuple[int, int, int, int] = (220, 100, 420, 340)):
        self._conf = conf
        self._box = box
        self._label: str | None = None

    @property
    def class_names(self) -> list[str]:
        return list(config.EMOTIONS)

    def force(self, label: str | None) -> None:
        self._label = label

    def detect(self, frame) -> Detection | None:
        if self._label is None:
            return None
        return Detection(label=self._label, conf=self._conf, box=self._box)
