"""Pruebas del ranking por emoción guardado en JSON."""

import json

from emotion_game.leaderboard import Leaderboard


def test_empty_when_file_does_not_exist(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json")
    assert board.top("Happy") == []


def test_add_returns_position_and_sorts_descending(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json")
    assert board.add("Happy", "Ana", 1000) == 1
    assert board.add("Happy", "Beto", 5000) == 1
    assert board.add("Happy", "Caro", 3000) == 2
    assert [e["nombre"] for e in board.top("Happy")] == ["Beto", "Caro", "Ana"]


def test_rankings_are_separate_per_emotion(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json")
    board.add("Happy", "Ana", 1000)
    board.add("Sad", "Beto", 2000)
    assert [e["nombre"] for e in board.top("Happy")] == ["Ana"]
    assert [e["nombre"] for e in board.top("Sad")] == ["Beto"]


def test_negative_scores_are_ranked(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json")
    board.add("Disgust", "Ana", -300)
    assert board.add("Disgust", "Beto", -50) == 1


def test_tie_keeps_earlier_entry_first(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json")
    board.add("Happy", "Ana", 1000)
    assert board.add("Happy", "Beto", 1000) == 2


def test_keeps_only_top_size(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json", size=3)
    for i, score in enumerate([100, 200, 300]):
        board.add("Happy", f"J{i}", score)
    assert board.add("Happy", "Bajo", 50) is None
    assert len(board.top("Happy")) == 3
    assert board.add("Happy", "Alto", 250) == 2
    assert [e["puntaje"] for e in board.top("Happy")] == [300, 250, 200]


def test_qualifies(tmp_path):
    board = Leaderboard(tmp_path / "ranking.json", size=2)
    assert board.qualifies("Happy", -999)
    board.add("Happy", "A", 100)
    board.add("Happy", "B", 200)
    assert not board.qualifies("Happy", 100)
    assert board.qualifies("Happy", 101)


def test_persists_to_disk(tmp_path):
    path = tmp_path / "ranking.json"
    Leaderboard(path).add("Happy", "Ana", 1234)
    assert Leaderboard(path).top("Happy")[0]["puntaje"] == 1234
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["Happy"][0]["nombre"] == "Ana"


def test_saves_accented_names(tmp_path):
    path = tmp_path / "ranking.json"
    Leaderboard(path).add("Happy", "Sebastián", 10)
    assert Leaderboard(path).top("Happy")[0]["nombre"] == "Sebastián"


def test_creates_missing_folder(tmp_path):
    path = tmp_path / "data" / "ranking.json"
    Leaderboard(path).add("Happy", "Ana", 1)
    assert path.exists()


def test_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "ranking.json"
    path.write_text("{no es json", encoding="utf-8")
    assert Leaderboard(path).top("Happy") == []
