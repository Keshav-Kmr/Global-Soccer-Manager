"""Template banks: MatchEvent type -> narrative text variants.

Data, not logic — see commentary/CLAUDE.md. Adding variety or a new event
type's phrasing means adding a string here, never touching generator.py.

POSSESSION_PROGRESS is the one event type with its own dedicated table
(PROGRESSION_TEMPLATES_BY_FLAVOR) instead of a flat list: which bank gets
picked depends on which attribute dominates the protagonist's profile, so
the same event type reads differently depending on who actually produced
it — see commentary/CLAUDE.md on attribute-flavored phrasing.
"""

from app.engine.events import EventType

TEMPLATES: dict[EventType, list[str]] = {
    EventType.KICKOFF: [
        "Kickoff! {team} get us underway.",
        "And we're off — {team} to get the game started.",
    ],
    EventType.TURNOVER: [
        "{team} lose possession.",
        "Possession changes hands, away from {team}.",
        "{team} give the ball away.",
    ],
    EventType.MOMENT_OF_BRILLIANCE: [
        "A moment of magic from {player}!",
        "{player} does something special there!",
        "Pure quality from {player}!",
    ],
    EventType.FOUL: [
        "Foul! {team} concede a free kick.",
        "The referee's whistle goes — foul against {team}.",
        "{tackler} catches {victim} — that's a foul.",
    ],
    EventType.CARD: [
        "It's a {color} card for {player}.",
        "{player} is booked — {color}!",
        "The referee reaches for the {color}: {player} is in the book.",
    ],
    EventType.INJURY: [
        "{player} is down and needs treatment.",
        "Concern here for {player} — they can't continue.",
        "That looks painful for {player}.",
    ],
    EventType.SHOT: [
        "{player} lets fly!",
        "{player} goes for goal!",
        "{player} strikes it!",
    ],
    EventType.GOAL: [
        "GOAL! {player} finds the net for {team}!",
        "It's in! {player} scores for {team}!",
        "{player} makes no mistake — {team} score!",
    ],
    EventType.SAVE: [
        "Saved! {keeper} holds on to it.",
        "What a stop from {keeper}! {player} denied!",
        "{keeper} keeps it out!",
    ],
    EventType.BLOCK: [
        "Blocked! The defense throws itself in the way.",
        "Charged down before it could threaten.",
        "Well blocked — {player}'s effort is stopped dead.",
    ],
    EventType.OFF_TARGET: [
        "Off target — no danger there.",
        "That's gone well wide from {player}.",
        "{player} can't keep that one on target.",
    ],
    EventType.TACTIC_CHANGE: [
        "{team} make a tactical switch.",
        "A change of approach from {team}.",
        "{team} rethink their setup.",
    ],
    EventType.SUBSTITUTION: [
        "A substitution for {team}: {player_in} replaces {player_out}.",
        "{team} make a change — {player_in} on for {player_out}.",
        "Fresh legs for {team}: on comes {player_in}.",
    ],
    EventType.FULL_TIME: [
        "That's full time!",
        "The final whistle blows.",
    ],
}

PROGRESSION_TEMPLATES_BY_FLAVOR: dict[str, list[str]] = {
    "pace": [
        "{player} explodes past a challenge!",
        "{player} races down the {phase}!",
        "{player} bursts through with real pace!",
    ],
    "dribbling": [
        "{player} dances past a challenge!",
        "{player} jinks past the defender!",
        "{player} glides through with a clever touch!",
    ],
    "vision": [
        "{player} picks out a teammate!",
        "{player} threads it through!",
        "{player} finds the perfect pass!",
    ],
    "default": [
        "{player} moves the ball forward.",
        "{player} keeps possession for {team}.",
        "{player} progresses the play.",
    ],
}

# Above this threshold on the 1-99 scale, an attribute is considered
# genuinely "dominant" enough to earn its own flavor; below it, phrasing
# falls back to the generic bank rather than reading as flashy for an
# unremarkable player.
FLAVOR_THRESHOLD = 70
