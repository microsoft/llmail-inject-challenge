from models import Team, to_api


def test_to_api():
    team = Team("Test Team")
    team.members = ["octocat"]

    api_team = to_api(team)

    assert api_team == {
        "team_id": team.team_id,
        "name": team.name,
        "members": team.members,
        "solved_scenarios": [],
        "is_enabled": True,
    }
