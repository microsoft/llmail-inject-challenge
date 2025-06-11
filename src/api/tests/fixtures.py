import uuid
import pytest
import services as services
from models import Team, User


@pytest.fixture
def test_storage() -> "StorageFixture":
    return StorageFixture()


class StorageFixture:
    def __init__(self):
        self.repo = services.StorageRepository(
            services.get_table_service_client("UseDevelopmentStorage=true")
        )
        self.queues = services.QueueRepository(
            services.get_queue_service_client("UseDevelopmentStorage=true")
        )

        self.repo.setup_tables()
        self.queues.setup_queues()

        self.__original_storage = services.STORAGE.storage
        self.__original_queues = services.STORAGE.queues

    def team(self):
        team = Team("Test Team", team_id="00000000-0000-0000-0000-000000000000", members=["test-user"])
        self.repo.upsert_team(team)

        return team

    def user(self, with_team: bool = True, admin: bool = False):
        user = User(
            "test-user",
            team="00000000-0000-0000-0000-000000000000" if with_team else None,
            role="admin" if admin else "competitor",
        )
        self.repo.upsert_user(user)

        return user

    def clean(self):
        for team in self.repo.list_teams():
            self.repo.delete_team(team)

        for user in self.repo.list_users():
            self.repo.delete_user(user)

        for scenario in self.repo.list_scenarios():
            self.repo.delete_scenario(scenario)

    def __enter__(self) -> services.StorageRepository:
        services.STORAGE.storage = self.repo
        services.STORAGE.queues = self.queues

        return self.repo

    def __exit__(self, exc_type, exc_val, exc_tb):
        services.STORAGE.storage = self.__original_storage
        services.STORAGE.queues = self.__original_queues
