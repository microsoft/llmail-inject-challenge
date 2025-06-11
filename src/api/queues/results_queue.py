import logging
import json
import os
import azure.functions as func
from azure.data.tables import TableClient, TableServiceClient
from azure.identity import DefaultAzureCredential
from datetime import datetime, timezone

from services import STORAGE, trace, tracer, SpanKind, Link
from models import JobResult

results_queue = func.Blueprint()


@results_queue.queue_trigger("msg", "results", connection="AzureWebJobsStorage")
def queue_results(msg: func.QueueMessage):
    """
    This function is triggered when a message is enqueued in the results queue.
    The message contains the job result, and the corresponding job ID is updated in Azure Table REPOS.storage.
    """
    try:
        # Get message content
        message_content = msg.get_body().decode("utf-8")
        logging.debug(f"Received message from queue: {message_content}")

        # Parse the message content
        job_result = JobResult(**json.loads(message_content))

        handler_context = trace.get_current_span().get_span_context()

        with tracer.start_as_current_span(
            "MSG :results",
            kind=SpanKind.CONSUMER,
            context=job_result.get_trace_context(),
            links=[Link(handler_context)],
            attributes={
                "job_id": job_result.job_id,
                "team_id": job_result.team_id,
            },
        ) as span:
            job = STORAGE.storage.get_job(job_result.team_id, job_result.job_id)
            if job is None:
                logging.error(
                    f"Job with ID {job_result.job_id} not found in datastores, considering this an invalid result."
                )
                return

            if job.completed_time is not None:
                logging.warning("Received multiple results for the same job, ignoring this one.")
            else:
                job.output = job_result.output
                job.started_time = job_result.started_time
                job.completed_time = job_result.completed_time
                job.objectives = job_result.objectives or {}
                STORAGE.storage.upsert_job(job)
                logging.debug(f"Updated job with ID {job_result.job_id} in Table REPOS.storage.")

            solved = job.objectives and all(job.objectives.values())

            if not solved:
                logging.info(f"Processed result for job {job_result.job_id} successfully (unsolved).")
                return

            team = STORAGE.storage.get_team(job.team_id)
            if not team or not team.is_enabled:
                logging.info(
                    f"Processed result for job {job_result.job_id} successfully (team not found or disabled)."
                )
                return

            if job.scenario in team.solved_scenarios:
                logging.info(
                    f"Processed result for job {job_result.job_id} successfully (scenario already solved)."
                )
                return

            scenario = STORAGE.storage.get_scenario(job.scenario)
            if not scenario:
                logging.error(f"Scenario with ID {job.scenario} not found in datastores.")
                return

            team.solved_scenarios.append(job.scenario)
            team.solution_details[job.scenario] = datetime.now(timezone.utc).isoformat()
            STORAGE.storage.upsert_team(team)

            scenario.solves += 1
            STORAGE.storage.upsert_scenario(scenario)

            logging.info(f"Processed result for job {job_result.job_id} successfully.")

    except Exception as e:
        logging.error(f"Error processing queue message, will retry later", exc_info=True)
        raise
