from app.engine.home_advantage import HOME_BONUS, HomeAdvantage


def test_home_team_gets_the_bonus():
    assert HomeAdvantage().modifier("home", home_team_id="home") == HOME_BONUS


def test_away_team_gets_no_bonus():
    assert HomeAdvantage().modifier("away", home_team_id="home") == 1.0
