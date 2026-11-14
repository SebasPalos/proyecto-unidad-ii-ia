"""Punto de entrada.

    python main.py          juega con el modelo entrenado (models/best.pt)
    python main.py --fake   modo de prueba: simula al modelo con el teclado
    python main.py --gris   cámara en escala de grises (o tecla G en el menú)
"""

import argparse
import sys

from emotion_game import config
from emotion_game.camera import Camera
from emotion_game.detector import FakeDetector
from emotion_game.game import EmotionGame
from emotion_game.leaderboard import Leaderboard


def main() -> None:
    parser = argparse.ArgumentParser(description="¡Convence a la IA! Juego de emociones con YOLO.")
    parser.add_argument("--fake", action="store_true", help="simular el modelo con el teclado")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, help="índice de la webcam")
    parser.add_argument("--gris", action="store_true",
                        help="iniciar con la cámara en escala de grises (también se cambia con G en el menú)")
    args = parser.parse_args()

    if args.fake:
        detector = FakeDetector()
    else:
        if not config.MODEL_PATH.exists():
            sys.exit(f"No encontré el modelo en {config.MODEL_PATH}. Usa --fake para probar sin modelo.")
        from emotion_game.detector import YoloDetector

        detector = YoloDetector()

    game = EmotionGame(detector, Camera(args.camera), Leaderboard(config.LEADERBOARD_PATH),
                       grayscale=args.gris)
    game.run()


if __name__ == "__main__":
    main()
