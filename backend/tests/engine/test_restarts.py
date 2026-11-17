"""Restarts (Laws 8–17 lightweight) — event presence and possession effects."""

import random
from unittest.mock import patch

from app.domain.match_context import MatchContext
from app.engine.card import Card
from app.engine.events import EventType
from app.engine.match import Match
from app.engine.match_situation import MatchSituation
from app.engine.phase import Phase
from app.engine.possession_chain import PossessionChainEngine
from app.engine.restart import RestartKind, shot_outcome_restart
from tests.factories import build_team


def _situation(home_id: str) -> MatchSituation:
    return MatchSituation(home_team_id=home_id, context=MatchContext(), referee_strictness=1.0)


def test_shot_outcome_maps_to_corner_or_goal_kick():
    assert shot_outcome_restart(EventType.BLOCK) == RestartKind.CORNER_KICK
    assert shot_outcome_restart(EventType.SAVE) == RestartKind.GOAL_KICK
    assert shot_outcome_restart(EventType.OFF_TARGET) == RestartKind.GOAL_KICK


def test_resolve_shot_blocked_emits_corner():
    home = build_team("home", "Home", 70)
    away = build_team("away", "Away", 70)
    engine = PossessionChainEngine()
    rng = random.Random(1)

    with (
        patch.object(rng, "choice", return_value=EventType.BLOCK),
        patch.object(engine._probability, "resolve", return_value=False),
    ):
        events, scored, _, follow = engine._resolve_shot(30, home, away, rng, _situation(home.id))  # noqa: SLF001

    assert scored is False
    assert EventType.CORNER_KICK in [e.type for e in events]
    assert follow == (home.id, Phase.FINAL_THIRD, "corner")


def test_foul_emits_free_kick_and_retains_attacker():
    home = build_team("home", "Home", 70)
    away = build_team("away", "Away", 70)
    engine = PossessionChainEngine()
    rng = random.Random(123)
    foul = type("FoulResult", (), {"is_foul": True, "severity": 0.8})()

    with patch.object(engine._foul, "roll", return_value=foul):
        with patch.object(engine._card, "roll", return_value=Card.NONE):
            with patch.object(engine._injury, "roll", return_value=False):
                with patch.object(engine._probability, "resolve", return_value=False):
                    result = engine.run(20, home, away, rng, _situation(home.id))

    assert any(e.type == EventType.FREE_KICK for e in result.events)
    assert result.next_possession_team_id == home.id
    assert result.possession_retained is True


def test_goal_emits_kickoff_for_conceding_team():
    home = build_team("home", "Home", 70)
    away = build_team("away", "Away", 70)
    match = Match(home, away, seed=100)
    with patch.object(match._chain_engine._probability, "resolve", side_effect=[True, True, True, True]):
        match.play_next_chain()
    kickoffs = [e for e in match.events if e.type == EventType.KICKOFF]
    assert len(kickoffs) >= 2  # opening kickoff + after goal


def test_full_match_includes_restart_events():
    home = build_team("home", "Home", 70)
    away = build_team("away", "Away", 70)
    match = Match(home, away, seed=4242)
    match.play_to_completion()
    restart_types = {EventType.GOAL_KICK, EventType.CORNER_KICK, EventType.FREE_KICK, EventType.THROW_IN}
    assert any(e.type in restart_types for e in match.events)