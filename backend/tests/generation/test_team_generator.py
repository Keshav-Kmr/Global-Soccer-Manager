import random

from app.domain.player import Position
from app.generation.team_generator import PlayerGenerator, TeamGenerator


def test_generated_team_has_the_right_shape():
    team = TeamGenerator(random.Random(1)).generate("FC Test", quality=65)

    assert len(team.starting_xi) == 11
    assert len(team.bench) == 5
    assert team.starting_xi[0].position == Position.GK


def test_generation_is_deterministic_given_the_same_seed():
    team_a = TeamGenerator(random.Random(1)).generate("FC Test", quality=65)
    team_b = TeamGenerator(random.Random(1)).generate("FC Test", quality=65)

    assert team_a.id == team_b.id
    assert [p.id for p in team_a.starting_xi] == [p.id for p in team_b.starting_xi]
    assert [p.attributes.pace for p in team_a.starting_xi] == [p.attributes.pace for p in team_b.starting_xi]


def test_different_seeds_produce_different_teams():
    team_a = TeamGenerator(random.Random(1)).generate("FC Test", quality=65)
    team_b = TeamGenerator(random.Random(2)).generate("FC Test", quality=65)

    assert team_a.id != team_b.id
    assert [p.id for p in team_a.starting_xi] != [p.id for p in team_b.starting_xi]


def test_attributes_cluster_around_the_requested_quality():
    generator = PlayerGenerator(random.Random(3))
    players = [generator.generate(Position.CM, quality=70) for _ in range(200)]

    average_pace = sum(p.attributes.pace for p in players) / len(players)

    assert 60 < average_pace < 80


def test_outfield_players_have_floor_goalkeeper_attributes():
    player = PlayerGenerator(random.Random(4)).generate(Position.ST, quality=70)

    assert player.attributes.reflexes == 1
    assert player.attributes.handling == 1
    assert player.attributes.gk_positioning == 1


def test_goalkeepers_get_real_goalkeeper_attributes():
    player = PlayerGenerator(random.Random(4)).generate(Position.GK, quality=70)

    assert player.attributes.reflexes > 1
