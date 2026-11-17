"""Offside detection on the normalized 0–100 pitch grid.

This is a structural check at the moment a pass is completed into the
attacking third: receiver position, second-last defender, ball position,
attacking direction, own-half safe harbour, backward-pass exception, and
level-with-second-last treated as onside. It does not replace full IFAB
interpretation (e.g. deliberate play deflections).
"""

from __future__ import annotations

_HALF_LINE = 50.0
_LEVEL_TOLERANCE = 0.25


def _sorted_defender_x(positions: list[float], *, attacks_right: bool) -> list[float]:
    if attacks_right:
        return sorted(positions, reverse=True)
    return sorted(positions)


def second_last_defender_x(
    defender_positions: list[tuple[float, float]],
    *,
    attacks_right: bool,
) -> float | None:
    """Depth coordinate of the second-last opponent (all outfield positions)."""
    if len(defender_positions) < 2:
        return None
    xs = _sorted_defender_x([p[0] for p in defender_positions], attacks_right=attacks_right)
    return xs[1]


class OffsideCheck:
    def is_offside(
        self,
        *,
        receiver_x: float,
        ball_x: float,
        defender_positions: list[tuple[float, float]],
        attacks_right: bool,
        involved_in_play: bool = True,
    ) -> bool:
        if not involved_in_play:
            return False

        if attacks_right:
            if receiver_x <= _HALF_LINE:
                return False
            if receiver_x < ball_x - _LEVEL_TOLERANCE:
                return False
        else:
            if receiver_x >= _HALF_LINE:
                return False
            if receiver_x > ball_x + _LEVEL_TOLERANCE:
                return False

        line_x = second_last_defender_x(defender_positions, attacks_right=attacks_right)
        if line_x is None:
            return False

        if attacks_right:
            return receiver_x > line_x + _LEVEL_TOLERANCE
        return receiver_x < line_x - _LEVEL_TOLERANCE