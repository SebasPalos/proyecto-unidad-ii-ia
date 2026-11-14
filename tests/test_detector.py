"""Pruebas de la selección del rostro del jugador y del detector falso."""

from emotion_game.detector import Detection, FakeDetector, pick_player


def det(label, conf, x1, y1, x2, y2):
    return Detection(label=label, conf=conf, box=(x1, y1, x2, y2))


def test_no_detections_returns_none():
    assert pick_player([]) is None


def test_picks_largest_box_not_highest_conf():
    small_sure = det("Happy", 0.95, 0, 0, 50, 50)
    big_player = det("Sad", 0.60, 100, 100, 400, 400)
    assert pick_player([small_sure, big_player]) is big_player


def test_fake_detector_returns_forced_label():
    fake = FakeDetector(conf=0.8)
    fake.force("Happy")
    result = fake.detect(frame=None)
    assert result.label == "Happy"
    assert result.conf == 0.8


def test_fake_detector_without_label_detects_nothing():
    fake = FakeDetector()
    fake.force(None)
    assert fake.detect(frame=None) is None
