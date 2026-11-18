"""Marcador flotante: formato, sincronía con el puntaje real, animación y posición."""

import pygame
import pytest

from emotion_game.score_marker import (
    FLASH_SECONDS,
    MAX_POPUPS,
    POPUP_SECONDS,
    ROLL_SECONDS,
    ScoreFx,
    format_multiplier,
    format_score,
    place_marker,
)
from emotion_game.scoring import Observation, ScoreKeeper

BOUNDS = pygame.Rect(18, 74, 924, 628)
SIZE = (260, 66)


@pytest.mark.parametrize(
    "score, text",
    [(0, "+000"), (80, "+080"), (-100, "-100"), (1250, "+1,250"), (-27500, "-27,500")],
)
def test_score_always_has_sign_and_three_digits(score, text):
    assert format_score(score) == text


def test_multiplier_format():
    assert format_multiplier(3) == "x3"
    assert format_multiplier(3, pending=True) == "x3.."


class TestScoreFx:
    def test_no_event_while_score_stays_the_same(self):
        fx = ScoreFx()
        # muchos cuadros de cámara sin cambio de puntaje: ningún evento
        assert [fx.update(0, i / 60) for i in range(120)] == [0] * 120
        assert fx.popups == []

    def test_one_event_per_change_with_its_delta(self):
        fx = ScoreFx()
        assert fx.update(80, 1.0) == 80
        assert fx.update(80, 1.01) == 0  # el mismo puntaje no vuelve a sonar
        assert fx.update(-20, 1.1) == -100
        assert fx.direction == -1

    def test_several_ticks_in_one_frame_are_a_single_event(self):
        keeper = ScoreKeeper("Happy")
        fx = ScoreFx()
        for _ in range(3):  # cuadro lento: cayeron 3 ticks juntos
            keeper.tick(Observation("Happy", 0.8))
        assert fx.update(keeper.score, 1.0) == 240
        assert len(fx.popups) == 1

    def test_shown_value_rolls_and_lands_on_the_real_score(self):
        fx = ScoreFx()
        fx.update(100, 1.0)
        halfway = fx.shown(1.0 + ROLL_SECONDS / 2)
        assert 0 < halfway < 100
        assert fx.shown(1.0 + ROLL_SECONDS) == 100
        assert fx.shown(99.0) == 100

    def test_roll_goes_down_when_points_are_lost(self):
        fx = ScoreFx(500)
        fx.update(300, 1.0)
        assert 300 < fx.shown(1.0 + ROLL_SECONDS / 2) < 500

    def test_roll_finishes_before_the_next_tick(self):
        from emotion_game import config

        assert ROLL_SECONDS < config.TICK_SECONDS

    def test_flash_starts_full_and_fades_out(self):
        fx = ScoreFx()
        assert fx.flash(0.5) == 0  # sin destello antes del primer cambio
        fx.update(50, 1.0)
        assert fx.flash(1.0) == 1
        assert 0 < fx.flash(1.0 + FLASH_SECONDS / 2) < 1
        assert fx.flash(1.0 + FLASH_SECONDS) == 0

    def test_popups_expire_and_are_capped(self):
        fx = ScoreFx()
        for i in range(10):
            fx.update((i + 1) * 10, 1.0 + i * 0.01)
        assert len(fx.popups) == MAX_POPUPS
        assert fx.live_popups(1.09 + POPUP_SECONDS + 0.01) == []

    def test_reset_clears_everything_for_a_new_round(self):
        fx = ScoreFx()
        fx.update(900, 1.0)
        fx.reset(0, 2.0)
        assert fx.shown(2.0) == 0
        assert fx.flash(2.0) == 0
        assert fx.popups == [] and fx.direction == 0

    def test_follows_the_real_keeper_score_through_a_whole_round(self):
        keeper = ScoreKeeper("Happy")
        fx = ScoreFx()
        events = []
        observations = [Observation("Happy", 0.8)] * 20 + [Observation(None, 0.0)] * 30
        for i, obs in enumerate(observations):
            before = keeper.score
            keeper.tick(obs)
            now = (i + 1) * 0.1
            for frame in range(6):  # 6 cuadros de cámara por tick
                delta = fx.update(keeper.score, now + frame / 60)
                if delta:
                    events.append(delta)
            assert (keeper.score != before) == (len(events) > 0 and events[-1] == keeper.score - before
                                                and fx.popups[-1].born == now)
            assert fx.shown(now + 0.099) == keeper.score
        assert sum(events) == keeper.score
        # los 2 ticks de debounce no cambian el puntaje, así que no generan evento
        assert len(events) == len(observations) - 2


class TestPlacement:
    def test_goes_above_the_head_to_the_right_of_the_emotion_tag(self):
        face = pygame.Rect(300, 260, 300, 340)
        tag = pygame.Rect(300, 224, 200, 36)
        rect = place_marker(SIZE, face, tag, BOUNDS)
        assert rect.left > tag.right
        assert rect.bottom < face.top

    def test_follows_the_face(self):
        tag_of = lambda face: pygame.Rect(face.left, face.top - 36, 200, 36)
        a = pygame.Rect(200, 260, 300, 340)
        b = a.move(150, 40)
        ra, rb = (place_marker(SIZE, f, tag_of(f), BOUNDS) for f in (a, b))
        assert (rb.x - ra.x, rb.y - ra.y) == (150, 40)

    @pytest.mark.parametrize(
        "face",
        [
            pygame.Rect(330, 110, 300, 360),  # cabeza pegada al HUD
            pygame.Rect(640, 240, 290, 340),  # pegado al borde derecho
            pygame.Rect(20, 240, 290, 340),  # pegado al borde izquierdo
            pygame.Rect(620, 80, 300, 360),  # esquina superior derecha
        ],
    )
    def test_never_covers_the_face_and_stays_on_screen(self, face):
        tag = pygame.Rect(face.left, max(70, face.top - 36), 200, 36)
        rect = place_marker(SIZE, face, tag, BOUNDS)
        assert BOUNDS.contains(rect)
        assert not rect.colliderect(face)
