from app.domain.player import Player, PlayerAttributes, Position
from app.engine.phase import Phase
from app.engine.rating.calculator import PhaseRatingCalculator


def _player(position: Position, **attrs) -> Player:
    defaults = dict(
        pace=1, dribbling=1, passing=1, vision=1, shooting=1, tackling=1,
        marking=1, strength=1, positioning=1, aggression=1, composure=1, stamina=1,
        flair=1,
    )
    defaults.update(attrs)
    return Player(id="p", name="Test Player", position=position, attributes=PlayerAttributes(**defaults))


def test_individual_score_is_the_exact_weighted_sum():
    # BUILD_UP attack weights: passing=0.5, composure=0.2, positioning=0.3
    player = _player(Position.CB, passing=80, composure=60, positioning=40)

    score = PhaseRatingCalculator().individual_score(Phase.BUILD_UP, player, "attack")

    expected = 80 * 0.5 + 60 * 0.2 + 40 * 0.3
    assert score == expected


def test_rate_is_the_average_of_eligible_players_only():
    # BUILD_UP attack-eligible positions are GK/CB/DM; a ST here must be excluded.
    eligible_one = _player(Position.CB, passing=90, composure=90, positioning=90)
    eligible_two = _player(Position.DM, passing=10, composure=10, positioning=10)
    not_eligible = _player(Position.ST, passing=99, composure=99, positioning=99)

    rating = PhaseRatingCalculator().rate(
        Phase.BUILD_UP, [eligible_one, eligible_two, not_eligible], "attack"
    )

    expected = (90 + 10) / 2  # every weight is applied equally to both eligible players
    assert rating == expected


def test_rate_falls_back_to_the_whole_squad_if_nobody_is_eligible():
    only_striker = _player(Position.ST, passing=50, composure=50, positioning=50)

    rating = PhaseRatingCalculator().rate(Phase.BUILD_UP, [only_striker], "attack")

    assert rating == 50 * 0.5 + 50 * 0.2 + 50 * 0.3
