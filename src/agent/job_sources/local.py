import argparse
import json

from agent import JobSource, Workload
from api.models import JobMessage, JobResult
from utils.better_logging import logger

local_job_source_args = argparse.ArgumentParser()
local_job_source_args.add_argument(
    "--job-file",
    default="job.json",
    help="Path to the job file (only used in local mode). Defaults to 'job.json'.",
)


# LocalTestAgent class
class LocalJobSource(JobSource):
    """
    Allows an agent workload to be executed from the command line (without a queue).
    Reads the job details from a JSON file.
    """

    def __init__(self, unknown_args: list[str]):
        args, _ = local_job_source_args.parse_known_args(unknown_args)

        self.json_file_path = args.job_file
        self.has_run = False

    async def get_next_job(self) -> JobMessage | None:
        """
        Reads the next job from a JSON file.
        """

        if self.has_run:
            return None

        try:
            with open(self.json_file_path, "r") as file:
                job_data = json.load(file)

        except FileNotFoundError:
            logger.error(f"Error: File '{self.json_file_path}' not found.")
            return
        except json.JSONDecodeError:
            logger.error(f"Error: File '{self.json_file_path}' is not a valid JSON file.")
            return

        self.has_run = True
        # Creating a JobMessage from JSON data
        job_data["job_id"] = job_data.pop("id")
        return JobMessage(**job_data)

    async def handle_result(self, job: JobMessage, result: JobResult):
        """
        Prints the result and raises an exception to indicate job execution is complete.
        """
        print(repr(result))
        logger.info(f"Job {result.job_id} completed.")
