import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from emotion_game import config, retro


@pytest.fixture(autouse=True, scope="module")
def pygame_ready():
    pygame.init()
    yield
    pygame.quit()


# ------------------------------------------------------------- caras pixel art


@pytest.mark.parametrize("label", list(config.EMOTIONS))
def test_every_emotion_has_its_own_color_and_face(label):
    assert label in retro.EMOTION_COLORS
    grid = retro.face_grid(label)
    assert len(grid) == retro.FACE_SIZE
    assert all(len(row) == retro.FACE_SIZE for row in grid)


@pytest.mark.parametrize("label", list(config.EMOTIONS))
def test_features_are_drawn_inside_the_face(label):
    grid = retro.face_grid(label)
    base = retro.BASE_FACE
    features = [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "F"]

    assert features, "cada cara necesita ojos y boca"
    assert all(base[y][x] == "Y" for x, y in features)


def test_each_emotion_looks_different():
    faces = {tuple(retro.face_grid(label)) for label in config.EMOTIONS}

    assert len(faces) == len(config.EMOTIONS)


def test_unknown_label_falls_back_to_neutral_face():
    assert retro.face_grid("Unicornio") == retro.face_grid("Natural")


def test_face_surface_scales_each_cell():
    surface = retro.face_surface("Happy", cell=5)

    assert surface.get_size() == (16 * 5, 16 * 5)


# ------------------------------------------------------------- fuente pixelada


def test_pixel_font_has_no_antialiasing():
    color = (255, 225, 77)
    surface = retro.PixelFont(32).render("¡Convence!", color)

    seen = {
        tuple(surface.get_at((x, y)))
        for x in range(surface.get_width())
        for y in range(surface.get_height())
    }
    assert seen <= {(*color, 255), (0, 0, 0, 0)}


def test_pixel_font_grows_in_whole_pixels():
    font = retro.PixelFont(48)
    surface = font.render("A", (255, 255, 255))

    assert font.scale >= 2
    assert surface.get_width() % font.scale == 0
    assert surface.get_height() % font.scale == 0


def test_bigger_size_means_bigger_text():
    small = retro.PixelFont(18).render("EMOCIÓN", (255, 255, 255))
    big = retro.PixelFont(72).render("EMOCIÓN", (255, 255, 255))

    assert big.get_height() > small.get_height()


# ------------------------------------------------------------- efectos


def test_scanlines_darken_one_row_every_gap():
    surface = retro.scanlines((10, 9), gap=3, alpha=60)

    alphas = [surface.get_at((0, y)).a for y in range(9)]
    assert alphas == [60, 0, 0, 60, 0, 0, 60, 0, 0]


def test_starfield_is_deterministic_and_inside_the_area():
    area = pygame.Rect(100, 50, 200, 300)

    first = retro.starfield(area, count=40, seed=7)
    second = retro.starfield(area, count=40, seed=7)

    assert first == second
    assert len(first) == 40
    assert all(area.collidepoint(x, y) for x, y, _, _ in first)


@pytest.mark.parametrize(
    "fraction, lit",
    [(0.0, 0), (1.0, 10), (0.5, 5), (0.01, 1), (1.7, 10), (-0.3, 0)],
)
def test_segments_lit_rounds_up_and_clamps(fraction, lit):
    assert retro.segments_lit(fraction, 10) == lit


def test_blink_alternates_each_half_period():
    assert retro.blink(0.1, period=1.0) is True
    assert retro.blink(0.6, period=1.0) is False
    assert retro.blink(1.1, period=1.0) is True


def test_mix_blends_and_clamps():
    assert retro.mix((0, 0, 0), (200, 100, 50), 0.5) == (100, 50, 25)
    assert retro.mix((0, 0, 0), (200, 100, 50), 2) == (200, 100, 50)
    assert retro.mix((10, 20, 30), (200, 100, 50), -1) == (10, 20, 30)


def test_pixel_box_cuts_the_corners():
    surface = pygame.Surface((40, 20), pygame.SRCALPHA)
    retro.pixel_box(surface, pygame.Rect(0, 0, 40, 20), (255, 0, 0), cut=4)

    assert surface.get_at((0, 0)).a == 0
    assert surface.get_at((39, 19)).a == 0
    assert tuple(surface.get_at((20, 0))) == (255, 0, 0, 255)
    assert tuple(surface.get_at((0, 10))) == (255, 0, 0, 255)
