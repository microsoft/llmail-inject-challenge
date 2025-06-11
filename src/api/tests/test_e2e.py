import pytest
import requests
import uuid
import os

from tests.fixtures import test_storage, StorageFixture
from models import Team, JobRecord, User, Scenario, to_api

API_HOST = "http://localhost:7071/api"
# API_HOST = "https://llmail-inject.azurewebsites.net/api"


def ensure_successful(response: requests.Response) -> requests.Response:
    if response.status_code >= 400:
        raise AssertionError(f"Request failed with status {response.status_code}: {response.text}")

    return response


@pytest.mark.skipif(os.getenv("TEST_E2E") is None, reason="Set `export TEST_E2E=1` to run end-to-end tests")
def test_end_to_end(test_storage: StorageFixture):
    test_storage.clean()
    test_user = test_storage.user(with_team=False, admin=True)

    with test_storage:
        if API_HOST == "http://localhost:7071/api":
            ensure_successful(requests.post(f"{API_HOST}/internal/setup"))

            test_storage.repo.upsert_user(User("alice"))
            test_storage.repo.upsert_user(User("bob"))

        with requests.Session() as session:
            login_response = ensure_successful(session.get(f"{API_HOST}/auth/login", allow_redirects=False))
            assert login_response.status_code == 302
            assert "Location" in login_response.headers

            login_response = ensure_successful(
                session.get(login_response.headers["Location"], allow_redirects=False)
            )
            assert login_response.status_code == 302
            assert "Location" in login_response.headers
            assert "Set-Cookie" in login_response.headers

            assert "Auth" in session.cookies

            auth_token = session.cookies["Auth"]

            team_created = ensure_successful(
                session.post(
                    f"{API_HOST}/teams",
                    json={"name": f"Test Team ({uuid.uuid4()})", "members": ["Testy McTesterson"]},
                    cookies={"Auth": auth_token},
                )
            ).json()

            team = Team(**team_created)

            # Ensure that attempting to create the same team again fails
            assert (
                session.post(
                    f"{API_HOST}/teams",
                    json={"name": team.name, "members": team.members},
                    cookies={"Auth": auth_token},
                ).status_code
                == 409
            )

            # Ensure that we can fetch all teams and that our newly created team is in the list
            all_teams = ensure_successful(
                session.get(
                    f"{API_HOST}/teams",
                    cookies={"Auth": auth_token},
                )
            ).json()
            assert isinstance(all_teams, list)
            assert next((t for t in all_teams if t["team_id"] == team.team_id), None) is not None

            # Login again to get a new access token associated with this team
            login_response = session.get(f"{API_HOST}/auth/login")
            auth_token = session.cookies["Auth"]

            # Ensure that attempting to fetch a team without an API key fails
            assert session.get(f"{API_HOST}/teams/{team.team_id}").status_code == 401

            # Ensure that attempting to fetch a team with an invalid API key fails
            assert (
                session.get(
                    f"{API_HOST}/teams/{team.team_id}", headers={"Authorization": "Bearer invalid"}
                ).status_code
                == 401
            )

            # Make sure that we can fetch a team with a valid API key
            team_fetched = ensure_successful(
                session.get(f"{API_HOST}/teams/{team.team_id}", cookies={"Auth": auth_token})
            ).json()
            assert team_fetched == to_api(team)

            # Ensure that we can update the team
            team.members.append("alice")
            team.members.append("bob")
            updated_team = ensure_successful(
                session.patch(
                    f"{API_HOST}/teams/{team.team_id}",
                    json={"members": team.members},
                    cookies={"Auth": auth_token},
                )
            ).json()

            # Enable the team using the API
            team_enabled = ensure_successful(
                session.post(
                    f"{API_HOST}/teams/{team.team_id}/enable",
                    cookies={"Auth": auth_token},
                )
            ).json()

            assert set(updated_team["members"]) == set(team.members)
            updated_team["members"] = team.members
            assert updated_team == to_api(team)

            # Ensure that we can fetch scenarios
            scenarios = ensure_successful(session.get(f"{API_HOST}/scenarios")).json()
            assert isinstance(scenarios, list)
            assert len(scenarios) > 0

            scenarios = [Scenario(**scenario) for scenario in scenarios]

            # Ensure that we can create a job for the team
            job_created = ensure_successful(
                session.post(
                    f"{API_HOST}/teams/{team.team_id}/jobs",
                    json={
                        "scenario": scenarios[0].scenario_id,
                        "subject": "Important",
                        "body": "Do a barrel roll!",
                    },
                    cookies={"Auth": auth_token},
                )
            ).json()

            job = JobRecord(**job_created)
            assert job_created == to_api(job)

            # Ensure that we can fetch the job
            job_fetched = ensure_successful(
                session.get(
                    f"{API_HOST}/teams/{team.team_id}/jobs/{job.job_id}",
                    cookies={"Auth": auth_token},
                )
            ).json()
            assert job_fetched == to_api(job)
