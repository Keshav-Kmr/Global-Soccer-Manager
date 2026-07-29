import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_test_helpers import make_team_payload, make_test_client


def test_create_and_get_team_round_trips():
    with make_test_client() as client:
        payload = make_team_payload("home", "FC Home")

        create_response = client.post("/teams", json=payload)
        assert create_response.status_code == 200

        get_response = client.get("/teams/home")
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["name"] == "FC Home"
        assert len(body["starting_xi"]) == 11


def test_get_unknown_team_is_404():
    with make_test_client() as client:
        response = client.get("/teams/does-not-exist")
        assert response.status_code == 404


def test_list_teams_returns_all_saved_teams():
    with make_test_client() as client:
        client.post("/teams", json=make_team_payload("home", "FC Home"))
        client.post("/teams", json=make_team_payload("away", "FC Away"))

        response = client.get("/teams")

        assert response.status_code == 200
        ids = {team["id"] for team in response.json()}
        assert ids == {"home", "away"}
