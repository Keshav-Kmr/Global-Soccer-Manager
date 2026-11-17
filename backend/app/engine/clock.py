"""Match clock: two halves plus stoppage time derived from interruptions."""

from enum import Enum

MINUTES_PER_CHAIN = 2
REGULATION_FIRST_HALF_END = 45
REGULATION_MATCH_END = 90

STOPPAGE_MIN = 1
STOPPAGE_MAX = 6

_INTERRUPTION_WEIGHT = {
    "goal": 45,
    "foul": 20,
    "card": 15,
    "injury": 60,
    "substitution": 30,
    "tactic_change": 10,
}


class MatchPeriod(str, Enum):
    FIRST_HALF = "first_half"
    SECOND_HALF = "second_half"
    FINISHED = "finished"


class MatchClock:
    def __init__(self) -> None:
        self.minute = 0
        self.period = MatchPeriod.FIRST_HALF
        self.first_half_stoppage = 0
        self.second_half_stoppage = 0
        self._interruption_seconds = 0
        self.halftime_minute: int | None = None

    def advance_chain(self) -> None:
        if self.period == MatchPeriod.FINISHED:
            return
        self.minute += MINUTES_PER_CHAIN
        self._maybe_fix_stoppage()

    def _maybe_fix_stoppage(self) -> None:
        if (
            self.period == MatchPeriod.FIRST_HALF
            and self.minute > REGULATION_FIRST_HALF_END
            and self.first_half_stoppage == 0
        ):
            self.first_half_stoppage = self._compute_stoppage()
            self._interruption_seconds = 0
        if (
            self.period == MatchPeriod.SECOND_HALF
            and self.minute > REGULATION_MATCH_END
            and self.second_half_stoppage == 0
        ):
            self.second_half_stoppage = self._compute_stoppage()
            self._interruption_seconds = 0

    def first_half_limit(self) -> int:
        stoppage = self.first_half_stoppage or STOPPAGE_MIN
        return REGULATION_FIRST_HALF_END + stoppage

    def match_limit(self) -> int:
        stoppage = self.second_half_stoppage or STOPPAGE_MIN
        return REGULATION_MATCH_END + stoppage

    def record_interruption(self, event_type: str) -> None:
        if self.period == MatchPeriod.FINISHED:
            return
        self._interruption_seconds += _INTERRUPTION_WEIGHT.get(event_type, 5)

    def should_emit_halftime(self) -> bool:
        if self.period != MatchPeriod.FIRST_HALF:
            return False
        if self.minute <= REGULATION_FIRST_HALF_END:
            return False
        self._maybe_fix_stoppage()
        return self.minute >= self.first_half_limit()

    def mark_halftime(self) -> None:
        self.halftime_minute = self.minute
        self.period = MatchPeriod.SECOND_HALF
        self._interruption_seconds = 0

    def should_finish(self) -> bool:
        if self.period != MatchPeriod.SECOND_HALF:
            return False
        if self.minute <= REGULATION_MATCH_END:
            return False
        self._maybe_fix_stoppage()
        return self.minute >= self.match_limit()

    def mark_finished(self) -> None:
        self.period = MatchPeriod.FINISHED

    def is_finished(self) -> bool:
        return self.period == MatchPeriod.FINISHED

    def _compute_stoppage(self) -> int:
        extra = self._interruption_seconds // 30
        return max(STOPPAGE_MIN, min(STOPPAGE_MAX, STOPPAGE_MIN + extra))


MATCH_MINUTES = REGULATION_MATCH_END