import os
import time
import json
from dataclasses import asdict
from azure.storage.queue import QueueServiceClient
from utils.better_logging import (
    logger,
)
from azure.identity import DefaultAzureCredential
from agent.job_source import JobSource
from api.models import JobMessage, JobResult, to_api

STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
QUEUE_STORAGE_CONNECTION_STRING = os.getenv("QUEUE_STORAGE_CONNECTION_STRING")

DEVELOPMENT_STORAGE_CONNECTION_STRING = """
""".replace(
    "\n", ""
).strip()


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
        credential=DefaultAzureCredential(),
    )


class AzureQueueJobSource(JobSource):
    """
    This agent will interact with an Azure queue to retrieve and handle jobs.
    """

    def __init__(self, unknown_args: list[str]):
        self.queue_client = get_queue_service_client()

        dispatch_queue_name = os.getenv("DISPATCH_QUEUE_NAME", "dispatch")
        result_queue_name = os.getenv("RESULT_QUEUE_NAME", "results")

        self.dispatch_queue_client = self.queue_client.get_queue_client(dispatch_queue_name)
        self.result_queue_client = self.queue_client.get_queue_client(result_queue_name)
        self.dead_letter_queue_client = self.queue_client.get_queue_client("dead-letter")

        logger.info(
            f"Azure Queue clients initialized: Dispatch Queue: {dispatch_queue_name}, Result Queue: {result_queue_name}"
        )

    async def get_next_job(self) -> JobMessage:
        """
        Fetch the next job from the Azure Queue and return it as a JobMessage.
        Returns None if no messages are in the queue.
        """
        while True:
            try:
                # Retrieve messages from the job queue
                logger.info("Attempting to retrieve a job from the dispatch queue.")
                messages = self.dispatch_queue_client.receive_messages(
                    messages_per_page=1, visibility_timeout=600
                )

                # Get the first message
                message = next(messages, None)

                if message is None:
                    logger.debug("No job messages found in the queue, retrying.")
                    time.sleep(10)
                    continue

                if message.dequeue_count and message.dequeue_count > 2:
                    logger.error(f"Job has been dequeued too many times, sending to dead-letter queue.")
                    self.dispatch_queue_client.delete_message(message)
                    self.dead_letter_queue_client.send_message(message.content)
                    continue

                # Create a JobMessage object from the message content
                job_message = JobMessage(
                    **{
                        k: v
                        for k, v in json.loads(message.content).items()
                        if k in JobMessage.__dataclass_fields__  # type: ignore[attr-defined]
                    }
                )

                job_message._internal_data["message_id"] = message.id
                job_message._internal_data["pop_receipt"] = message.pop_receipt

                logger.debug(f"Parsed JobMessage: {job_message}")

                # Delete the message from the queue after successful processing
                # self.dispatch_queue_client.delete_message(message)
                logger.debug(
                    f"Successfully processed and deleted the job message with ID: {job_message.job_id}"
                )

                return job_message

            except Exception as e:
                logger.error(f"Failed to retrieve job from Azure queue: {str(e)}")
                raise RuntimeError(f"Failed to retrieve job from Azure queue: {str(e)}")

    async def handle_result(self, job: JobMessage, result: "JobResult"):
        """
        Send a JobResult object to the result queue.
        """
        try:
            # Log the result data
            logger.debug(f"Preparing to enqueue JobResult for job {result.job_id}")

            # Convert the dictionary to JSON
            message_content = json.dumps(to_api(result))

            # Send the JobResult to the result queue
            self.result_queue_client.send_message(message_content)
            logger.debug(f"Successfully enqueued JobResult with ID: {result.job_id}")

            # Delete the queue message so that we don't run this again
            self.dispatch_queue_client.delete_message(
                job._internal_data["message_id"], job._internal_data["pop_receipt"]
            )

        except Exception as e:
            logger.error(f"Failed to enqueue result to Azure queue: {str(e)}")
            raise Exception(f"Failed to enqueue result to Azure queue: {str(e)}")
