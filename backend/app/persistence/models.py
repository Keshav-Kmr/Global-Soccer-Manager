"""SQLAlchemy ORM models. These are the persistence layer's own vocabulary
— distinct from app/domain (the simulation's internal world) and
delivery/schemas.py (the API wire contract). Repositories are the only
code that translates between these three; nothing else imports this
module. See backend/CLAUDE.md on why the layers stay separate.

A player only exists as part of a team's roster (no free-agent pool yet —
that's transfer-market scope, README roadmap Phase 7), so `PlayerModel` is
a straightforward child table with no independent repository. `Tactic`
fields live flat on `TeamModel`: a team always owns exactly one tactic, so
a separate join table would be pure ceremony.
"""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base


class TeamModel(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    mentality: Mapped[str]
    tempo: Mapped[str]
    pressing: Mapped[str]
    width: Mapped[str]
    defensive_line: Mapped[str]
    marking_scheme: Mapped[str]
    formation: Mapped[str] = mapped_column(default="4-3-3")

    players: Mapped[list["PlayerModel"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class PlayerModel(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    is_bench: Mapped[bool]
    name: Mapped[str]
    position: Mapped[str]

    pace: Mapped[int]
    dribbling: Mapped[int]
    passing: Mapped[int]
    vision: Mapped[int]
    shooting: Mapped[int]
    tackling: Mapped[int]
    marking: Mapped[int]
    strength: Mapped[int]
    positioning: Mapped[int]
    aggression: Mapped[int]
    composure: Mapped[int]
    stamina: Mapped[int]
    flair: Mapped[int]
    reflexes: Mapped[int]
    handling: Mapped[int]
    gk_positioning: Mapped[int]

    team: Mapped["TeamModel"] = relationship(back_populates="players")


class MatchResultModel(Base):
    """A finished match's durable record — the in-memory MatchRepository
    (app/persistence/in_memory_repository.py) holds the *live*, in-progress
    event log for streaming and is deliberately not this: writing every
    event to disk in real time would be needless I/O for state nobody
    needs to survive a restart mid-match. This table is written once, when
    MatchService sees the match finish."""

    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(primary_key=True)
    team_a_id: Mapped[str]
    team_a_name: Mapped[str]
    team_b_id: Mapped[str]
    team_b_name: Mapped[str]
    score_a: Mapped[int]
    score_b: Mapped[int]
    seed: Mapped[int]
    events_json: Mapped[str]
