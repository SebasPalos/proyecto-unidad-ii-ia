"""Pruebas de las reglas de puntaje del juego.

Reglas (acordadas con el equipo):
- La ronda dura 100 ticks de 0.1 s (10 segundos), según config.ROUND_TICKS.
- Emoción pedida: suma int(conf * 100) * multiplicador.
- Otra emoción: resta int(conf * 100) * multiplicador.
- Sin detección: resta 100 * multiplicador.
- El multiplicador empieza en x1 y sube +1 cada 5 ticks seguidos en el mismo estado.
- Un cambio de estado (positivo <-> negativo) solo se confirma tras 3 ticks seguidos.
  Mientras se confirma, no se suma ni se resta y el multiplicador se congela.
  Al confirmarse, el nuevo estado empieza en x1.
"""

import pytest

from emotion_game import config
from emotion_game.scoring import Observation, ScoreKeeper

TARGET = "Happy"


def happy(conf=1.0):
    return Observation(label="Happy", conf=conf)


def sad(conf=1.0):
    return Observation(label="Sad", conf=conf)


def nothing():
    return Observation(label=None, conf=0.0)


def play(keeper, observations):
    for obs in observations:
        keeper.tick(obs)
    return keeper


class TestTargetEmotion:
    def test_first_tick_adds_conf_times_100(self):
        keeper = ScoreKeeper(TARGET)
        keeper.tick(happy(0.80))
        assert keeper.score == 80

    def test_conf_is_truncated_to_integer(self):
        keeper = ScoreKeeper(TARGET)
        keeper.tick(happy(0.876))
        assert keeper.score == 87

    def test_multiplier_rises_every_five_ticks(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.5)] * 5)
        assert keeper.multiplier == 1
        assert keeper.score == 5 * 50
        keeper.tick(happy(0.5))
        assert keeper.multiplier == 2
        assert keeper.score == 5 * 50 + 100

    def test_perfect_round_scores_27500(self):
        keeper = play(ScoreKeeper(TARGET), [happy(1.0)] * 50)
        assert keeper.score == 27_500
        assert keeper.multiplier == 10


class TestPenalties:
    def test_wrong_emotion_subtracts_with_its_conf(self):
        keeper = ScoreKeeper(TARGET)
        keeper.tick(sad(0.70))
        assert keeper.score == -70

    def test_no_detection_subtracts_fixed_100(self):
        keeper = ScoreKeeper(TARGET)
        keeper.tick(nothing())
        assert keeper.score == -100

    def test_negative_multiplier_also_grows(self):
        keeper = play(ScoreKeeper(TARGET), [nothing()] * 6)
        assert keeper.score == -(5 * 100 + 200)

    def test_wrong_emotion_and_no_detection_share_negative_streak(self):
        keeper = play(ScoreKeeper(TARGET), [sad(0.5)] * 5 + [nothing()])
        assert keeper.multiplier == 2
        assert keeper.score == -(5 * 50 + 200)

    def test_worst_round_scores_minus_27500(self):
        keeper = play(ScoreKeeper(TARGET), [nothing()] * 50)
        assert keeper.score == -27_500


class TestDebounce:
    def test_single_flicker_is_ignored_and_freezes_multiplier(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.5)] * 6)  # 250 + 100 = 350, x2
        keeper.tick(sad(0.9))
        assert keeper.score == 350
        assert keeper.multiplier == 2
        keeper.tick(happy(0.5))
        assert keeper.score == 450
        assert keeper.multiplier == 2

    def test_two_pending_ticks_score_nothing(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.5)] * 3)
        play(keeper, [sad(0.5)] * 2)
        assert keeper.score == 150

    def test_change_confirms_on_third_tick_with_multiplier_reset(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.5)] * 10)  # 250 + 500 = 750, x2
        play(keeper, [sad(0.4)] * 3)
        assert keeper.multiplier == 1
        assert keeper.score == 750 - 40

    def test_returning_to_target_restarts_at_x1(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.5)] * 10)
        play(keeper, [nothing()] * 3)  # 750 - 100
        play(keeper, [happy(0.5)] * 3)  # se confirma en el tercero: +50
        assert keeper.multiplier == 1
        assert keeper.score == 750 - 100 + 50

    def test_first_tick_sets_state_without_debounce(self):
        keeper = ScoreKeeper(TARGET)
        keeper.tick(nothing())
        assert keeper.score == -100


class TestRoundLength:
    def test_default_round_lasts_10_seconds(self):
        assert config.ROUND_TICKS * config.TICK_SECONDS == pytest.approx(10.0)
        assert ScoreKeeper(TARGET).remaining_seconds == pytest.approx(10.0)

    def test_round_finishes_after_round_ticks(self):
        keeper = play(ScoreKeeper(TARGET), [happy()] * (config.ROUND_TICKS - 1))
        assert not keeper.finished
        keeper.tick(happy())
        assert keeper.finished

    def test_ticks_after_finish_are_ignored(self):
        keeper = play(ScoreKeeper(TARGET), [happy(1.0)] * config.ROUND_TICKS)
        final = keeper.score
        keeper.tick(happy(1.0))
        assert keeper.score == final

    def test_short_round_still_works(self):
        keeper = play(ScoreKeeper(TARGET, round_ticks=50), [happy(1.0)] * 51)
        assert keeper.finished
        assert keeper.score == 27_500

    def test_remaining_seconds(self):
        keeper = play(ScoreKeeper(TARGET), [happy()] * 20)
        assert keeper.remaining_seconds == pytest.approx(8.0)


class TestStats:
    def test_tracks_best_conf_and_ticks_on_target(self):
        keeper = play(ScoreKeeper(TARGET), [happy(0.6), happy(0.9), sad(0.99), happy(0.7)])
        assert keeper.best_conf == pytest.approx(0.9)
        assert keeper.target_ticks == 3
