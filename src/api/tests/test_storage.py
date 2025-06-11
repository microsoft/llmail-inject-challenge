import pytest
import uuid
from services.storage import StorageRepository, User, Team, JobRecord
from tests.fixtures import test_storage, StorageFixture


def test_team(test_storage: StorageFixture):
    test_storage.clean()

    with test_storage as repo:
        assert repo.get_team(str(uuid.uuid4())) is None

        team = Team("Test Team")
        team.members = ["Alice"]

        repo.upsert_team(team)

        assert repo.get_team(team.team_id) == team
        assert team in repo.list_teams()

        team.members = ["Alice", "Bob"]

        repo.upsert_team(team)

        assert repo.get_team(team.team_id) == team
        assert team in repo.list_teams()

        repo.delete_team(team)
        assert repo.get_team(team.team_id) is None


def test_job(test_storage: StorageFixture):
    test_storage.clean()

    with test_storage as repo:
        team = Team("Test Team")
        repo.upsert_team(team)

        assert repo.get_team(team.team_id) == team

        job = JobRecord(team.team_id, "gpt", "Important", "Do a barrel roll!")
        repo.upsert_job(job)

        assert repo.get_job(team.team_id, job.job_id) == job
        assert repo.list_jobs(team.team_id) == [job]

        repo.delete_job(job)
        assert repo.get_job(team.team_id, job.job_id) is None
        assert repo.list_jobs(team.team_id) == []

        repo.upsert_job(job)
        assert repo.get_job(team.team_id, job.job_id) == job

        # Make sure that cleaning up a team also cleans up its jobs
        repo.delete_team(team)
        assert repo.get_team(team.team_id) is None
        assert repo.get_job(team.team_id, job.job_id) is None


def test_user(test_storage: StorageFixture):
    test_storage.clean()

    with test_storage as repo:
        user = User("test_user")
        repo.upsert_user(user)

        assert repo.get_user(user.login) == user

        user.team = "test_team"
        repo.upsert_user(user)

        assert repo.get_user(user.login) == user

        repo.delete_user(user)
        assert repo.get_user(user.login) is None
