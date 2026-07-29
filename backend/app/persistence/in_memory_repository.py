"""InMemoryMatchRepository: the only MatchRepository implementation for
now — a plain dict, living for the lifetime of the process. Matches don't
survive a restart; see root CLAUDE.md on persistence being deferred until
there's a real need for a database.
"""

from app.persistence.repository import MatchRepository


class InMemoryMatchRepository(MatchRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create(self, match_id: str) -> None:
        self._sessions[match_id] = {"events": [], "finished": False}

    def append_event(self, match_id: str, event: dict) -> None:
        self._sessions[match_id]["events"].append(event)

    def get_events(self, match_id: str, since_index: int = 0) -> list[dict]:
        return self._sessions[match_id]["events"][since_index:]

    def mark_finished(self, match_id: str) -> None:
        self._sessions[match_id]["finished"] = True

    def is_finished(self, match_id: str) -> bool:
        return self._sessions[match_id]["finished"]

    def exists(self, match_id: str) -> bool:
        return match_id in self._sessions
