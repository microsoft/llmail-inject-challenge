from abc import ABC, abstractmethod
from api.models import JobMessage, JobResult
from utils.better_logging import logger


# Base Agent class
class JobSource(ABC):
    @abstractmethod
    async def get_next_job(self) -> JobMessage | None:
        pass

    @abstractmethod
    async def handle_result(self, job: JobMessage, result: JobResult):
        pass

    async def handle_job_failure(self, job: JobMessage, result: JobResult | None, ex: Exception):
        print(f"{job} failed with exception {ex}")
