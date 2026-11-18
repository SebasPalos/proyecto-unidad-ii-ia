"""Captura de la webcam con OpenCV y conversión a superficies de Pygame."""

import sys

import cv2
import numpy as np
import pygame


def capture_backend(platform: str = sys.platform) -> int:
    """Backend de OpenCV según el sistema: así el mismo código abre la cámara en Windows y Mac.

    CAP_DSHOW abre la cámara mucho más rápido en Windows; en Mac hace falta AVFoundation.
    En cualquier otro sistema dejamos que OpenCV elija.
    """
    return {"win32": cv2.CAP_DSHOW, "darwin": cv2.CAP_AVFOUNDATION}.get(platform, cv2.CAP_ANY)


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480):
        self._width = width
        self._height = height
        self._cap = cv2.VideoCapture(index, capture_backend())
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    @property
    def available(self) -> bool:
        return self._cap.isOpened()

    def read(self) -> np.ndarray:
        """Devuelve el cuadro en BGR y en espejo; si no hay cámara, un cuadro negro."""
        ok, frame = self._cap.read() if self.available else (False, None)
        if not ok:
            return np.zeros((self._height, self._width, 3), dtype=np.uint8)
        return cv2.flip(frame, 1)

    def release(self) -> None:
        self._cap.release()


def to_grayscale(frame: np.ndarray) -> np.ndarray:
    """Escala de grises, pero con 3 canales iguales porque YOLO espera imágenes BGR.

    Casi todas las fotos de Asco del dataset vienen de CK+, que está en blanco y negro.
    Pasar la webcam a grises acerca lo que ve el modelo a lo que vio al entrenar.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def frame_to_surface(frame: np.ndarray, size: tuple[int, int]) -> pygame.Surface:
    rgb = cv2.cvtColor(cv2.resize(frame, size), cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(rgb.tobytes(), size, "RGB")
