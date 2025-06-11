from abc import ABC, abstractmethod
from api.models import JobMessage, JobResult
from utils.better_logging import logger


class Workload(ABC):
    def __init__(self, kind: str):
        self.kind = kind

    @abstractmethod
    async def execute(self, job: JobMessage) -> JobResult:
        pass
