"""Parámetros del juego. Cambiar aquí, no dentro de la lógica."""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_DIR / "models" / "best.pt"
BASE_MODEL_PATH = PROJECT_DIR / "models" / "yolo11n.pt"
DATASET_DIR = PROJECT_DIR / "datasets" / "emociones"
RUNS_DIR = PROJECT_DIR / "runs" / "detect"
LEADERBOARD_PATH = PROJECT_DIR / "data" / "leaderboard.json"

# Reglas del puntaje
TICK_SECONDS = 0.1
ROUND_TICKS = 50  # 5 segundos
MULTIPLIER_STEP_TICKS = 5  # +1 al multiplicador cada 0.5 s seguidos
DEBOUNCE_TICKS = 3  # 0.3 s seguidos para confirmar un cambio de estado
NO_DETECTION_PENALTY = 100

# Detección
DETECTION_CONF = 0.25
CAMERA_INDEX = 0

# Ranking
LEADERBOARD_SIZE = 10
NAME_MAX_LENGTH = 12

# Nombres de clase tal como vienen en el data.yaml del dataset -> texto en pantalla
EMOTIONS = {
    "Happy": "Felicidad",
    "Sad": "Tristeza",
    "Angry": "Enojo",
    "Surprise": "Sorpresa",
    "Disgust": "Asco",
    "Natural": "Neutral",
}
