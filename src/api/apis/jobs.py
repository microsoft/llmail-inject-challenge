import azure.functions as func
import json
import logging
import urllib.parse
from datetime import datetime, timezone

from models import User, Team, JobRecord, JobMessage, to_api

from .mixins import (
    authenticated,
    instrumented,
    error_handler,
    require_team_membership,
)
from services import STORAGE, RateLimiter
from .errors import error_response

jobs = func.Blueprint()

DEFAULT_RATE_LIMIT_SUSTAINED = 1.0
DEFAULT_RATE_LIMIT_BURST = 10
DEFAULT_RATE_LIMIT_TOTAL = 60000

# The competition launch date that defines when we start accepting job submissions.
LAUNCH_DATE = datetime.strptime("2025-03-13T11:00:00Z", "%Y-%m-%dT%H:%M:%SZ").astimezone(timezone.utc)
# The competition end date which can be None if there is none defined. If defined, we stop accepting job submissions after this date.
END_DATE = datetime.strptime("2025-04-17T11:59:00Z", "%Y-%m-%dT%H:%M:%SZ").astimezone(timezone.utc)


@jobs.route("api/teams/{team_id}/jobs", methods=["GET"])
@error_handler
@instrumented("/api/teams/{team_id}/jobs")
@authenticated
@require_team_membership
async def jobs_list(req: func.HttpRequest, user: User) -> func.HttpResponse:
    team_id = req.route_params.get("team_id")

    if team_id == "mine":
        team_id = user.team

    if not team_id:
        return error_response(
            400,
            "Your request URL does not include valid team ID in the /api/teams/{team_id}/... portion of the request.",
            "Please make sure that you have filled in your team ID correctly when creating the URL, or if you are using /api/teams/mine/... ensure that you are a member of a team.",
        )

    jobs = STORAGE.storage.list_jobs(team_id)

    return func.HttpResponse(
        json.dumps([to_api(job) for job in jobs]),
        status_code=200,
        mimetype="application/json",
    )


@jobs.route("api/teams/{team_id}/jobs", methods=["POST"])
@error_handler
@instrumented("/api/teams/{team_id}/jobs")
@authenticated
@require_team_membership
async def jobs_create(req: func.HttpRequest, user: User) -> func.HttpResponse:
    team_id = req.route_params.get("team_id")

    if team_id == "mine":
        team_id = user.team

    if not team_id:
        return error_response(
            400,
            "Your request URL does not include valid team ID in the /api/teams/{team_id}/... portion of the request.",
            "Please make sure that you have filled in your team ID correctly when creating the URL, or if you are using /api/teams/mine/... ensure that you are a member of a team.",
        )

    if user.role == "competitor":
        now = datetime.now(tz=timezone.utc)

        if now < LAUNCH_DATE:
            return error_response(
                400,
                "The competition has not started yet, and job submissions are blocked until the competition begins.",
                f"The competition will start at {LAUNCH_DATE.isoformat()}, and try again after the competition has started.",
            )
        elif END_DATE is not None and now > END_DATE:
            return error_response(
                400,
                "This phase of the competition has ended and we are no longer accepting job submissions. Please wait for announcements regarding the next phase of the competition to start.",
                f"This phase of the competition ended on {END_DATE.isoformat()}, and you can no longer submit jobs. Please wait for the next phase of the competition to start.",
            )

    try:
        # Step 1: Validate the team
        logging.debug(f"Validating team {team_id}.")
        team_info = STORAGE.storage.get_team(team_id)
        if not team_info or not team_info.is_enabled:
            if not team_info:
                logging.error(
                    f"Team with ID {team_id} not found after passing auth check (unclean deletion of a team?)."
                )
            else:
                logging.warning(f"Team {team_id} is not enabled, job creation was blocked.")
            return error_response(
                400,
                "The team you attempted to schedule a job for does not exist or is not enabled.",
                "Please make sure that you are using the correct team ID and that the competition is still active.",
            )

        logging.debug(f"Team {team_id} validated successfully: {team_info}")

        # Step 3: Check rate limits
        logging.debug(f"Checking rate limits for team {team_id}.")
        rate_limiter = RateLimiter(
            sustained_rate=team_info.rate_limit_sustained or DEFAULT_RATE_LIMIT_SUSTAINED,
            burst_size=team_info.rate_limit_burst or DEFAULT_RATE_LIMIT_BURST,
        )

        allowed, watermark = rate_limiter.try_make_request(team_info.rate_limit_watermark)

        if allowed and team_info.rate_limit_counter >= (
            team_info.rate_limit_total or DEFAULT_RATE_LIMIT_TOTAL
        ):
            allowed = False

        if not allowed:
            logging.warning(
                f"Rate limit exceeded for team {team_id} (counter: {team_info.rate_limit_counter}, watermark: {watermark})."
            )

            return error_response(
                429,
                "You have exceeded your job submission rate limit and cannot submit more jobs at this time.",
                "Please wait a few minutes and try again, we also recommend spacing out your submissions to avoid hitting limits. Keep in mind that rate limits are enforced at the team level.",
            )

        team_info.rate_limit_watermark = watermark.timestamp()
        team_info.rate_limit_counter += 1

        # Step 3: Process the job creation
        logging.debug(f"Parsing job record from request payload for team {team_id}.")
        job = _build_job(team_id, req)

        scenario = STORAGE.storage.get_scenario(job.scenario)
        if not scenario:
            logging.error(f"Scenario {scenario} not found.")
            return error_response(
                400,
                "The scenario you specified for the job does not exist or is not enabled.",
                "Please make sure that you are using the correct scenario ID and that the competition is still active.",
            )

        # Store the job in Azure Table Storage
        logging.debug(f"Saving job {job.job_id} to Jobs table")
        STORAGE.storage.upsert_job(job)

        # Send the job to the dispatch queue
        logging.debug(f"Sending job {job.job_id} to dispatch queue '{scenario.workqueue}'")
        STORAGE.queues.enqueue_job(job, queue_name=scenario.workqueue)

        # Update the team's rate limit watermark with the new value
        STORAGE.storage.upsert_team(team_info)

        logging.info(f"Job {job.job_id} created for team {team_id} and dispatched successfully.")
        return func.HttpResponse(
            json.dumps(to_api(job)),
            status_code=201,
            mimetype="application/json",
            headers={
                "Location": f"/api/teams/{team_id}/jobs/{job.job_id}",
            },
        )

    except ValueError as e:
        logging.warning(f"Invalid job data", exc_info=True)
        return error_response(
            400,
            "The job definition you provided could not be parsed or was missing a required property.",
            "Please make sure that you are using the correct job definition format and that your request contains valid JSON before trying again.",
        )


@jobs.route("api/teams/{team_id}/jobs/{job_id}", methods=["GET"])
@error_handler
@instrumented("/api/teams/{team_id}/jobs/{job_id}")
@authenticated
@require_team_membership
async def jobs_get(req: func.HttpRequest, user: User) -> func.HttpResponse:
    team_id = req.route_params.get("team_id")
    job_id = req.route_params.get("job_id")

    if team_id == "mine":
        team_id = user.team

    if not team_id:
        return error_response(
            400,
            "Your request URL does not include valid team ID in the /api/teams/{team_id}/... portion of the request.",
            "Please make sure that you have filled in your team ID correctly when creating the URL, or if you are using /api/teams/mine/... ensure that you are a member of a team.",
        )

    job = STORAGE.storage.get_job(team_id, job_id)
    if job is None:
        return error_response(
            404,
            "The job you requested could not be found.",
            "Please make sure that you have provided the correct team and job ID fields in your request.",
        )

    return func.HttpResponse(
        json.dumps(to_api(job)),
        status_code=200,
        mimetype="application/json",
    )


def _build_job(team_id: str, req: func.HttpRequest) -> JobRecord:
    """
    Builds a JobRecord object from the request data.
    """
    job_data = req.get_json()
    logging.debug(f"Received job data: {job_data}")

    # Validate and extract required fields
    scenario = job_data.get("scenario")
    if not scenario:
        raise ValueError("Missing required field: 'scenario'.")

    subject = job_data.get("subject")
    if not subject:
        raise ValueError("Missing required field: 'subject'.")

    body = job_data.get("body")
    if not body:
        raise ValueError("Missing required field: 'body'.")

    # Create the JobRecord object
    job = JobRecord(
        team_id=team_id,
        scenario=scenario,
        subject=subject,
        body=body,
    )

    return job
