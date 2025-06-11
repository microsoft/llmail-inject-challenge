import logging
import json
import os
import azure.functions as func
from azure.data.tables import TableClient, TableServiceClient
from azure.identity import DefaultAzureCredential

from services import STORAGE, trace, tracer, SpanKind, Link
from models import JobMessage
from datetime import datetime, timezone

deadletter_queue = func.Blueprint()


@deadletter_queue.queue_trigger("msg", "dead-letter", connection="AzureWebJobsStorage")
def queue_deadletter(msg: func.QueueMessage):
    """
    This function is triggered when a message is added to the dead-letter queue by the agent (following a repeated failure to successfully process it).
    """
    try:
        # Get message content
        message_content = msg.get_body().decode("utf-8")
        logging.debug(f"Received message from queue: {message_content}")

        # Parse the message content
        job_message = JobMessage(**json.loads(message_content))

        handler_context = trace.get_current_span().get_span_context()

        with tracer.start_as_current_span(
            "MSG :dead-letter",
            kind=SpanKind.CONSUMER,
            context=job_message.get_trace_context(),
            links=[Link(handler_context)],
            attributes={
                "job_id": job_message.job_id,
                "team_id": job_message.team_id,
                "scenario": job_message.scenario,
            },
        ) as span:
            job = STORAGE.storage.get_job(job_message.team_id, job_message.job_id)
            if job is None:
                logging.error(
                    f"Job with ID {job_message.job_id} not found in datastores, considering this an invalid result."
                )
                return

            if job.completed_time is not None:
                logging.info(
                    f"Job with ID {job_message.job_id} already completed, ignoring dead letter entry."
                )

                return

            job.output = f"Job failed to process after multiple attempts. Please report this issue to the competition organizers with the trace ID {trace.format_trace_id(trace.get_current_span().get_span_context().trace_id)}."
            job.started_time = datetime.now(timezone.utc).isoformat()
            job.completed_time = datetime.now(timezone.utc).isoformat()
            job.objectives = {}
            STORAGE.storage.upsert_job(job)
            logging.debug(f"Updated job with ID {job_message.job_id} in Table REPOS.storage.")

            logging.info(f"Processed dead letter entry for job {job_message.job_id} successfully.")

    except Exception as e:
        logging.error(f"Error processing queue message, will retry later", exc_info=True)
        raise
