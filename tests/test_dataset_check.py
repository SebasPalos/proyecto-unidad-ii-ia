"""Pruebas de la verificación del dataset antes de entrenar (manual, sección 8, punto 4)."""

import pytest

from emotion_game.dataset_check import DatasetError, check_dataset

CLASSES = ["Angry", "Disgust", "Happy", "Natural", "Sad", "Surprise"]


def make_dataset(root, counts, names=CLASSES, labels=None):
    labels = labels or counts
    lines = ["train: ../train/images", "val: ../valid/images", "test: ../test/images",
             f"nc: {len(names)}", f"names: {names}"]
    root.mkdir(parents=True, exist_ok=True)
    (root / "data.yaml").write_text("\n".join(lines), encoding="utf-8")
    for split, n in counts.items():
        (root / split / "images").mkdir(parents=True)
        (root / split / "labels").mkdir(parents=True)
        for i in range(n):
            (root / split / "images" / f"{i}.jpg").write_bytes(b"")
        for i in range(labels[split]):
            (root / split / "labels" / f"{i}.txt").write_text("0 0.5 0.5 0.2 0.2")
    return root


def test_valid_dataset_reports_counts(tmp_path):
    root = make_dataset(tmp_path / "ds", {"train": 7, "valid": 2, "test": 1})
    report = check_dataset(root)
    assert report.counts == {"train": 7, "valid": 2, "test": 1}
    assert report.names == CLASSES


def test_missing_data_yaml(tmp_path):
    with pytest.raises(DatasetError, match="data.yaml"):
        check_dataset(tmp_path)


def test_missing_split_folder(tmp_path):
    root = make_dataset(tmp_path / "ds", {"train": 3, "valid": 1})
    with pytest.raises(DatasetError, match="test"):
        check_dataset(root)


def test_images_and_labels_must_match(tmp_path):
    counts = {"train": 5, "valid": 2, "test": 1}
    root = make_dataset(tmp_path / "ds", counts, labels={"train": 4, "valid": 2, "test": 1})
    with pytest.raises(DatasetError, match="train"):
        check_dataset(root)


def test_class_names_must_match_the_game(tmp_path):
    root = make_dataset(tmp_path / "ds", {"train": 1, "valid": 1, "test": 1},
                        names=["angry", "disgust", "happy", "natural", "sad", "surprise"])
    with pytest.raises(DatasetError, match="clases"):
        check_dataset(root)
