import pytest
import json

import azure.functions as func

from models import Team, JobRecord
from apis.teams import teams_create, team_enable, team_disable
import apis.jobs as jobs
from tests.fixtures import StorageFixture, test_storage


def test_team_is_created_in_enabled_state_with_no_members():
    team = Team("Best AI researchers ever.")
    assert team.is_enabled is True and len(team.members) == 0


def test_enable_team_state():
    team = Team("Best AI researchers ever.")
    team.enable_team()
    assert team.is_enabled is True


def test_disable_team_state():
    team = Team("Best AI researchers ever.")
    team.disable_team()
    assert team.is_enabled is False


@pytest.mark.asyncio
async def test_team_can_not_submit_job_when_disabled(test_storage: StorageFixture):
    team = test_storage.team()
    user = test_storage.user()

    with test_storage as repo:
        # Disable the team
        team.disable_team()
        repo.upsert_team(team)

        # Allow the user to bypass the start time constraint
        user.role = "admin"
        repo.upsert_user(user)

        func_call = jobs.jobs_create.build().get_user_function()

        req = func.HttpRequest(
            method="POST",
            url="/teams/{team.team_id}/jobs",
            body=json.dumps(
                {"scenario": "level1a", "subject": "This is a test", "body": "Do a barrel roll!"}
            ).encode("utf-8"),
            route_params={"team_id": team.team_id},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user.auth_token()}"},
        )

        job_api_result = await func_call(req)
        assert job_api_result.status_code == 400
        assert (
            f"The team you attempted to schedule a job for does not exist or is not enabled."
            in job_api_result.get_body().decode()
        )
