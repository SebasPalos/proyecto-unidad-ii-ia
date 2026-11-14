"""Ranking por emoción, guardado en un archivo JSON local."""

import json
from datetime import datetime
from pathlib import Path

from emotion_game import config


class Leaderboard:
    def __init__(self, path: Path, size: int = config.LEADERBOARD_SIZE):
        self._path = Path(path)
        self._size = size
        self._data = self._load()

    def top(self, emotion: str) -> list[dict]:
        return list(self._data.get(emotion, []))

    def qualifies(self, emotion: str, score: int) -> bool:
        entries = self._data.get(emotion, [])
        return len(entries) < self._size or score > entries[-1]["puntaje"]

    def add(self, emotion: str, name: str, score: int) -> int | None:
        """Agrega el puntaje y devuelve su posición (1 = primero), o None si no entró al top."""
        if not self.qualifies(emotion, score):
            return None
        entries = self._data.setdefault(emotion, [])
        position = sum(1 for e in entries if e["puntaje"] >= score)
        entries.insert(position, {
            "nombre": name,
            "puntaje": score,
            "fecha": datetime.now().isoformat(timespec="seconds"),
        })
        del entries[self._size:]
        self._save()
        return position + 1

    def _load(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
