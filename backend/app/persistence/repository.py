"""MatchRepository: the interface MatchService depends on for anything
that needs to outlive a single function call — never a concrete database
client directly (backend/CLAUDE.md). Stores plain, already-serialized
event dicts (the WebSocket wire format from delivery/schemas.py), not
domain/engine objects — this keeps persistence generic and lets the
in-memory implementation be swapped for a real database later without any
caller (MatchService, routes) changing.
"""

from abc import ABC, abstractmethod


class MatchRepository(ABC):
    @abstractmethod
    def create(self, match_id: str) -> None:
        """Registers a new, empty match session."""

    @abstractmethod
    def append_event(self, match_id: str, event: dict) -> None:
        ...

    @abstractmethod
    def get_events(self, match_id: str, since_index: int = 0) -> list[dict]:
        """Events from `since_index` onward — 0 gets the full backlog."""

    @abstractmethod
    def mark_finished(self, match_id: str) -> None:
        ...

    @abstractmethod
    def is_finished(self, match_id: str) -> bool:
        ...

    @abstractmethod
    def exists(self, match_id: str) -> bool:
        ...
