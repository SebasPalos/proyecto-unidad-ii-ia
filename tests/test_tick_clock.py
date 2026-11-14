"""Pruebas del reloj de ticks: el puntaje depende del tiempo, no de los FPS."""

from emotion_game.tick_clock import TickClock


def test_no_ticks_before_first_interval():
    clock = TickClock(interval=0.1, start=10.0)
    assert clock.due(10.05) == 0


def test_one_tick_per_interval():
    clock = TickClock(interval=0.1, start=10.0)
    assert clock.due(10.1) == 1
    assert clock.due(10.15) == 0
    assert clock.due(10.2) == 1


def test_slow_frame_returns_several_ticks():
    clock = TickClock(interval=0.1, start=10.0)
    assert clock.due(10.35) == 3


def test_same_tick_count_regardless_of_fps():
    fast = TickClock(interval=0.1, start=0.0)
    slow = TickClock(interval=0.1, start=0.0)
    fast_total = sum(fast.due(i / 60) for i in range(1, 301))  # 60 FPS durante 5 s
    slow_total = sum(slow.due(i / 8) for i in range(1, 41))  # 8 FPS durante 5 s
    assert fast_total == slow_total == 50
