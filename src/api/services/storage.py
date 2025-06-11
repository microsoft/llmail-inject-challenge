import azure.core.exceptions
from azure.data.tables import TableServiceClient, UpdateMode
from azure.storage.queue import QueueServiceClient
from azure.identity import DefaultAzureCredential
import dataclasses
import os
from typing import Callable, T
import logging
from dataclasses import asdict
import json

from .telemetry import tracer, SpanKind
from models import *

STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
TABLE_STORAGE_CONNECTION_STRING = os.getenv("TABLE_STORAGE_CONNECTION_STRING")
QUEUE_STORAGE_CONNECTION_STRING = os.getenv("QUEUE_STORAGE_CONNECTION_STRING")

DEVELOPMENT_STORAGE_CONNECTION_STRING = """
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;
AccountKey=;
BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;
QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;
TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;
""".replace(
    "\n", ""
).strip()

default_credential = DefaultAzureCredential()


def get_table_service_client(
    connection_string: str | None = TABLE_STORAGE_CONNECTION_STRING,
) -> TableServiceClient:
    if connection_string is not None:
        return TableServiceClient.from_connection_string(connection_string)

    if STORAGE_ACCOUNT_NAME is None:
        return TableServiceClient.from_connection_string(DEVELOPMENT_STORAGE_CONNECTION_STRING)

    return TableServiceClient(
        account_name=STORAGE_ACCOUNT_NAME,
        endpoint=f"https://{STORAGE_ACCOUNT_NAME}.table.core.windows.net",
        credential=default_credential,
    )


def get_queue_service_client(
    connection_string: str | None = QUEUE_STORAGE_CONNECTION_STRING,
) -> QueueServiceClient:
    if connection_string == "UseDevelopmentStorage=true":
        return QueueServiceClient.from_connection_string(DEVELOPMENT_STORAGE_CONNECTION_STRING)

    if connection_string is not None:
        return QueueServiceClient.from_connection_string(connection_string)

    if STORAGE_ACCOUNT_NAME is None:
        return QueueServiceClient.from_connection_string(DEVELOPMENT_STORAGE_CONNECTION_STRING)

    return QueueServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.queue.core.windows.net",
        credential=default_credential,
    )


class QueueRepository:
    def __init__(self, queue_service_client: QueueServiceClient | None = None):
        self.queue_service_client = queue_service_client or get_queue_service_client()

        self._results_client = self.queue_service_client.get_queue_client("results")

    def setup_queues(self, extra: list[str] = []):
        with tracer.start_as_current_span("QueueRepository.setup_queues"):
            self.ensure_queue_exists("results")
            self.ensure_queue_exists("dispatch")
            self.ensure_queue_exists("dead-letter")

            for queue_name in extra:
                self.ensure_queue_exists(queue_name)

    def enqueue_job(self, job: JobRecord, queue_name: str):
        with tracer.start_as_current_span(
            "QueueRepository.enqueue_job", kind=SpanKind.PRODUCER, attributes={"job_id": job.job_id}
        ) as span:
            message = job.build_message()
            span.set_attribute("queue_name", queue_name)

            queue_client = self.queue_service_client.get_queue_client(queue_name)

            logging.debug(f"Enqueuing job {job.job_id} for team {job.team_id} in queue {queue_name}")
            queue_client.send_message(json.dumps(to_api(message)))
            logging.debug(f"Job {job.job_id} enqueued successfully.")

    def ensure_queue_exists(self, queue_name: str):
        try:
            self.queue_service_client.create_queue(queue_name)
        except azure.core.exceptions.ResourceExistsError:
            pass


class StorageRepository:
    def __init__(self, table_service_client: TableServiceClient | None = None):
        self.table_service_client = table_service_client or get_table_service_client()

        self._job_client = self.table_service_client.get_table_client("Jobs")
        self._team_client = self.table_service_client.get_table_client("Teams")
        self._scenario_client = self.table_service_client.get_table_client("Scenarios")
        self._user_client = self.table_service_client.get_table_client("Users")
        self._leaderboard_client = self.table_service_client.get_table_client("Leaderboards")

    def setup_tables(self):
        with tracer.start_as_current_span("StorageRepository.setup_queues"):
            self.table_service_client.create_table_if_not_exists("Jobs")
            self.table_service_client.create_table_if_not_exists("Teams")
            self.table_service_client.create_table_if_not_exists("Scenarios")
            self.table_service_client.create_table_if_not_exists("Users")
            self.table_service_client.create_table_if_not_exists("Leaderboards")

    def upsert_team(self, team: Team):
        with tracer.start_as_current_span(
            "StorageRepository.upsert_team", attributes={"team_id": team.team_id, "storage.table": "Teams"}
        ):
            self._team_client.upsert_entity(entity=serialize_entity(team), mode=UpdateMode.REPLACE)

    def get_team(self, team_id: str) -> Team | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_team", attributes={"team_id": team_id, "storage.table": "Teams"}
        ):
            try:
                entity = self._team_client.get_entity(partition_key=team_id, row_key=team_id)

                return deserialize_entity(entity, Team)
            except azure.core.exceptions.ResourceNotFoundError:
                return None
            except Exception as ex:
                logging.error(f"Error fetching team {team_id}", exc_info=True)
                raise

    def get_team_by_name(self, team_name: str) -> Team | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_team_by_name",
            attributes={"team_name": team_name, "storage.table": "Teams"},
        ):
            try:
                team_name = team_name.replace("'", "''")
                entities = self._team_client.query_entities(f"name eq '{team_name}'")
                teams = [
                    entity
                    for entity in (deserialize_entity(entity, Team) for entity in entities)
                    if entity is not None
                ]
                return teams[0] if teams else None
            except Exception as ex:
                logging.error(f"Error fetching team {team_name}", exc_info=True)
                raise

    def list_teams(self) -> list[Team]:
        with tracer.start_as_current_span(
            "StorageRepository.list_teams", attributes={"storage.table": "Teams"}
        ):
            try:
                entities = self._team_client.list_entities()
                return [
                    entity
                    for entity in (deserialize_entity(entity, Team) for entity in entities)
                    if entity is not None
                ]
            except Exception as ex:
                logging.error("Error fetching teams", exc_info=True)
                raise

    def delete_team(self, team: Team):
        with tracer.start_as_current_span(
            "StorageRepository.delete_team", attributes={"team_id": team.team_id, "storage.table": "Teams"}
        ):
            self._team_client.delete_entity(partition_key=team.partition_key(), row_key=team.row_key())

            for job in self.list_jobs(team.team_id):
                self.delete_job(job)

    def upsert_job(self, job: JobRecord):
        with tracer.start_as_current_span(
            "StorageRepository.upsert_job",
            attributes={"team_id": job.team_id, "job_id": job.job_id, "storage.table": "Jobs"},
        ):
            self._job_client.upsert_entity(entity=serialize_entity(job), mode=UpdateMode.REPLACE)

    def get_job(self, team_id: str, job_id: str) -> JobRecord | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_job",
            attributes={"team_id": team_id, "job_id": job_id, "storage.table": "Jobs"},
        ):
            try:
                entity = self._job_client.get_entity(partition_key=team_id, row_key=job_id)
                if entity is None:
                    return None

                return deserialize_entity(entity, JobRecord)
            except azure.core.exceptions.ResourceNotFoundError:
                return None
            except Exception as ex:
                logging.error(f"Error fetching job {job_id} for team {team_id}", exc_info=True)
                raise

    def list_jobs(self, team_id: str) -> list[JobRecord]:
        with tracer.start_as_current_span(
            "StorageRepository.list_jobs", attributes={"team_id": team_id, "storage.table": "Jobs"}
        ):
            try:
                entities = self._job_client.query_entities(f"PartitionKey eq '{team_id}'")
                return [
                    entity
                    for entity in (deserialize_entity(entity, JobRecord) for entity in entities)
                    if entity is not None
                ]
            except Exception as ex:
                logging.error(f"Error fetching jobs for team {team_id}", exc_info=True)
                raise

    def delete_job(self, job: JobRecord):
        with tracer.start_as_current_span(
            "StorageRepository.delete_job",
            attributes={"team_id": job.team_id, "job_id": job.job_id, "storage.table": "Jobs"},
        ):
            self._job_client.delete_entity(partition_key=job.partition_key(), row_key=job.row_key())

    def upsert_scenario(self, scenario: Scenario):
        with tracer.start_as_current_span(
            "StorageRepository.upsert_scenario",
            attributes={"scenario_id": scenario.scenario_id, "storage.table": "Scenarios"},
        ):
            self._scenario_client.upsert_entity(entity=serialize_entity(scenario), mode=UpdateMode.REPLACE)

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_scenario",
            attributes={"scenario_id": scenario_id, "storage.table": "Scenarios"},
        ):
            try:
                entity = self._scenario_client.get_entity(partition_key=scenario_id, row_key=scenario_id)
                return deserialize_entity(entity, Scenario)
            except azure.core.exceptions.ResourceNotFoundError:
                return None
            except Exception as ex:
                logging.error(f"Error fetching scenario {scenario_id}", exc_info=True)
                raise

    def list_scenarios(self) -> list[Scenario]:
        with tracer.start_as_current_span(
            "StorageRepository.list_scenarios", attributes={"storage.table": "Scenarios"}
        ):
            try:
                entities = self._scenario_client.list_entities()
                return [
                    entity
                    for entity in (deserialize_entity(entity, Scenario) for entity in entities)
                    if entity is not None and entity.phase == int(os.getenv("COMPETITION_PHASE", 2))
                ]
            except Exception as ex:
                logging.error("Error fetching scenarios", exc_info=True)
                raise

    def delete_scenario(self, scenario: Scenario):
        with tracer.start_as_current_span(
            "StorageRepository.delete_scenario",
            attributes={"scenario_id": scenario.scenario_id, "storage.table": "Scenarios"},
        ):
            self._scenario_client.delete_entity(
                partition_key=scenario.partition_key(), row_key=scenario.row_key()
            )

    def upsert_user(self, user: User):
        with tracer.start_as_current_span(
            "StorageRepository.upsert_user",
            attributes={"login": user.login, "storage.table": "Users"},
        ):
            self._user_client.upsert_entity(entity=serialize_entity(user), mode=UpdateMode.REPLACE)

    def get_user(self, login: str) -> User | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_user",
            attributes={"login": login, "storage.table": "Users"},
        ):
            try:
                entity = self._user_client.get_entity(partition_key=login, row_key=login)
                return deserialize_entity(entity, User)
            except azure.core.exceptions.ResourceNotFoundError:
                return None
            except Exception as ex:
                logging.error(f"Error fetching user {login}", exc_info=True)
                raise

    def list_users(self, team: str | None = None) -> list[User]:
        with tracer.start_as_current_span(
            "StorageRepository.list_users", attributes={"storage.table": "Users"}
        ):
            try:
                if team:
                    entities = self._user_client.query_entities(f"team eq '{team}'")
                else:
                    entities = self._user_client.list_entities()

                return [
                    entity
                    for entity in (deserialize_entity(entity, User) for entity in entities)
                    if entity is not None
                ]
            except Exception as ex:
                logging.error("Error fetching users", exc_info=True)
                raise

    def delete_user(self, user: User):
        with tracer.start_as_current_span(
            "StorageRepository.delete_user",
            attributes={"login": user.login, "storage.table": "Users"},
        ):
            self._user_client.delete_entity(partition_key=user.partition_key(), row_key=user.row_key())

    def upsert_leaderboard(self, leaderboard: Leaderboard):
        with tracer.start_as_current_span(
            "StorageRepository.upsert_leaderboard",
            attributes={"storage.table": "Leaderboards"},
        ):
            self._leaderboard_client.upsert_entity(
                entity=serialize_entity(leaderboard), mode=UpdateMode.REPLACE
            )

    def get_leaderboard(self) -> Leaderboard | None:
        with tracer.start_as_current_span(
            "StorageRepository.get_leaderboard",
            attributes={"storage.table": "Leaderboards"},
        ):
            phase = int(os.getenv("COMPETITION_PHASE", 2))
            try:
                entity = self._leaderboard_client.get_entity(
                    partition_key="leaderboard", row_key=f"leaderboard_phase{phase}"
                )
                return deserialize_entity(entity, Leaderboard)
            except azure.core.exceptions.ResourceNotFoundError:
                return None
            except Exception as ex:
                logging.error("Error fetching leaderboard", exc_info=True)
                raise


def deserialize_entity(data: dict, entity_class: Callable[..., T]) -> T | None:
    try:
        json_fields = getattr(entity_class, "__json_fields__", [])
        return entity_class(
            **{
                k: json.loads(v) if k in json_fields else v
                for k, v in data.items()
                if k in entity_class.__dataclass_fields__  # type: ignore[attr-defined]
            }
        )
    except:
        logging.error(f"Error deserializing entity {entity_class.__name__} from {data}", exc_info=True)
        return None


def serialize_entity(entity: T) -> dict:
    json_fields = getattr(entity, "__json_fields__", [])

    return {
        **{k: json.dumps(v) if k in json_fields else v for k, v in asdict(entity).items()},
        "PartitionKey": entity.partition_key(),
        "RowKey": entity.row_key(),
    }


class RepoContainer:
    def __init__(self, storage: "StorageRepository|None" = None, queues: "QueueRepository|None" = None):
        self.storage = storage or StorageRepository()
        self.queues = queues or QueueRepository()


STORAGE = RepoContainer()
