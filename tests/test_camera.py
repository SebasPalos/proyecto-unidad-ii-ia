import numpy as np

from emotion_game.camera import to_grayscale


def make_frame():
    frame = np.zeros((4, 6, 3), dtype=np.uint8)
    frame[:, :3] = (255, 0, 0)  # azul en BGR
    frame[:, 3:] = (0, 0, 255)  # rojo en BGR
    return frame


def test_keeps_shape_and_type_so_yolo_still_gets_three_channels():
    gray = to_grayscale(make_frame())

    assert gray.shape == (4, 6, 3)
    assert gray.dtype == np.uint8


def test_all_channels_are_equal():
    gray = to_grayscale(make_frame())

    assert np.array_equal(gray[..., 0], gray[..., 1])
    assert np.array_equal(gray[..., 1], gray[..., 2])


def test_uses_luminance_so_different_colors_get_different_grays():
    gray = to_grayscale(make_frame())

    # Con la fórmula de luminancia el rojo se ve más claro que el azul
    assert gray[0, 5, 0] > gray[0, 0, 0]


def test_does_not_modify_the_original_frame():
    frame = make_frame()
    original = frame.copy()

    to_grayscale(frame)

    assert np.array_equal(frame, original)
