import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from emotion_game import sound


def dominant_hz(wave: np.ndarray, rate: int = sound.SAMPLE_RATE) -> float:
    spectrum = np.abs(np.fft.rfft(wave.astype(float)))
    return float(np.fft.rfftfreq(len(wave), 1 / rate)[spectrum.argmax()])


def test_waves_are_short_16_bit_and_do_not_clip():
    for wave in (sound.gain_wave(), sound.loss_wave()):
        assert wave.dtype == np.int16
        assert 0.05 < len(wave) / sound.SAMPLE_RATE < 0.2
        assert 0 < np.abs(wave).max() < 32767
        assert wave[0] == 0 and wave[-1] == 0  # sin clics


def test_gain_is_high_pitched_and_loss_is_low():
    assert dominant_hz(sound.gain_wave()) > 800
    assert dominant_hz(sound.loss_wave()) < 250


def test_streaks_shift_the_pitch():
    assert dominant_hz(sound.gain_wave(9)) > dominant_hz(sound.gain_wave(0))
    assert dominant_hz(sound.loss_wave(9)) < dominant_hz(sound.loss_wave(0))


class FakeChannel:
    def __init__(self):
        self.played = []

    def play(self, snd):
        self.played.append(snd)


@pytest.fixture
def sounds():
    pygame.mixer.quit()
    try:
        pygame.mixer.init(sound.SAMPLE_RATE, -16, 1, 256)
    except pygame.error:
        pytest.skip("sin dispositivo de audio")
    bank = sound.ScoreSounds()
    bank._channel = FakeChannel()
    yield bank
    pygame.mixer.quit()


def test_plays_gain_for_positive_and_loss_for_negative(sounds):
    assert sounds.enabled
    assert sounds.play_score_change(80) == "gain"
    assert sounds.play_score_change(-100) == "loss"
    assert sounds._channel.played == [sounds._gain[0], sounds._loss[0]]


def test_no_sound_without_a_score_change(sounds):
    assert sounds.play_score_change(0) is None
    assert sounds._channel.played == []


def test_multiplier_picks_the_pitch_and_is_clamped(sounds):
    sounds.play_score_change(80, multiplier=3)
    sounds.play_score_change(80, multiplier=99)
    assert sounds._channel.played == [sounds._gain[2], sounds._gain[-1]]


def test_game_keeps_running_without_audio(monkeypatch):
    pygame.mixer.quit()

    def boom(*args, **kwargs):
        raise pygame.error("sin audio")

    monkeypatch.setattr(pygame.mixer, "init", boom)
    bank = sound.ScoreSounds()
    assert not bank.enabled
    assert bank.play_score_change(50) == "gain"  # no truena, solo no suena
