"""Unit tests for offside geometry (not full IFAB compliance)."""

from app.engine.offside import OffsideCheck


def test_receiver_in_own_half_never_offside_attacking_right():
    check = OffsideCheck()
    defenders = [(80.0, 40.0), (75.0, 50.0), (70.0, 60.0)]
    assert not check.is_offside(
        receiver_x=48.0,
        ball_x=55.0,
        defender_positions=defenders,
        attacks_right=True,
    )


def test_clearly_offside_beyond_second_last():
    check = OffsideCheck()
    defenders = [(85.0, 45.0), (78.0, 50.0), (70.0, 55.0)]
    assert check.is_offside(
        receiver_x=82.0,
        ball_x=75.0,
        defender_positions=defenders,
        attacks_right=True,
    )


def test_level_with_second_last_is_onside():
    check = OffsideCheck()
    defenders = [(85.0, 45.0), (78.0, 50.0), (70.0, 55.0)]
    assert not check.is_offside(
        receiver_x=78.0,
        ball_x=72.0,
        defender_positions=defenders,
        attacks_right=True,
    )


def test_backward_pass_not_offside():
    check = OffsideCheck()
    defenders = [(85.0, 45.0), (78.0, 50.0)]
    assert not check.is_offside(
        receiver_x=80.0,
        ball_x=82.0,
        defender_positions=defenders,
        attacks_right=True,
    )


def test_not_involved_not_offside():
    check = OffsideCheck()
    defenders = [(85.0, 45.0), (78.0, 50.0)]
    assert not check.is_offside(
        receiver_x=90.0,
        ball_x=70.0,
        defender_positions=defenders,
        attacks_right=True,
        involved_in_play=False,
    )