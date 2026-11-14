"""Verifica el dataset exportado de Roboflow antes de entrenar.

Si un split perdió su carpeta labels al descomprimir, el entrenamiento termina con
métricas en 0.0 (manual, sección 9). Mejor detectarlo antes de esperar una hora.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from emotion_game import config

SPLITS = ("train", "valid", "test")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DatasetError(Exception):
    pass


@dataclass
class DatasetReport:
    counts: dict[str, int]
    names: list[str]


def check_dataset(root: Path) -> DatasetReport:
    root = Path(root)
    yaml_path = root / "data.yaml"
    if not yaml_path.exists():
        raise DatasetError(f"No existe {yaml_path}. ¿Descomprimiste el zip en esa carpeta?")

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = list(data["names"].values()) if isinstance(data["names"], dict) else list(data["names"])
    if set(names) != set(config.EMOTIONS):
        raise DatasetError(
            f"Las clases del dataset {names} no coinciden con las del juego {list(config.EMOTIONS)}"
        )

    counts = {}
    for split in SPLITS:
        images_dir, labels_dir = root / split / "images", root / split / "labels"
        if not images_dir.is_dir() or not labels_dir.is_dir():
            raise DatasetError(f"Falta {split}/images o {split}/labels. Vuelve a descomprimir el zip.")
        images = sum(1 for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
        labels = sum(1 for p in labels_dir.iterdir() if p.suffix == ".txt")
        if images != labels:
            raise DatasetError(f"{split}: {images} imágenes pero {labels} labels. Vuelve a descomprimir el zip.")
        counts[split] = images

    return DatasetReport(counts=counts, names=names)
