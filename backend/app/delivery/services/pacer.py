"""Pacer: the only place in this codebase that deals with asyncio.sleep /
wall-clock time. See delivery/CLAUDE.md — this is what keeps the engine a
plain, deterministic, real-time-agnostic generator: the exact same
Match.play_next_chain() call can run in a tight loop (tests, "simulate
1000 matches" tooling) or be paced out live for a viewer, with Pacer being
the only difference between the two.

v1: a single fixed real-seconds-per-game-minute. Speed multipliers and
per-viewer pace are plausible follow-ups, not MVP scope.
"""

import asyncio

REAL_SECONDS_PER_GAME_MINUTE = 0.3


class Pacer:
    def __init__(self, seconds_per_game_minute: float = REAL_SECONDS_PER_GAME_MINUTE) -> None:
        # Overridable per instance — tests inject a near-zero pace rather
        # than waiting out a real 90-minute-equivalent match.
        self._seconds_per_game_minute = seconds_per_game_minute

    async def wait(self, game_minutes_elapsed: int) -> None:
        await asyncio.sleep(game_minutes_elapsed * self._seconds_per_game_minute)
