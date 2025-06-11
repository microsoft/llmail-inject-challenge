# Accessing the API

In addition to being able to submit challenge attempts through this website, you can also use
the API to submit attempts programmatically.

## Authentication
API requests require you to provide your API key with all requests in the `Authorization` header.
You will receive your API key when registering a new team, and we recommend keeping it safely stored
in a password manager, along with your Team ID. Without these, you will not be able to access the API
or use the website.

```http
GET /api/teams/mine HTTP/1.1
Authorization: Bearer ${apiKey}
Accept: application/json; charset=utf-8
Host: ${apiHost}
```

## Error Responses
When an error occurs, the API will return an appropriate HTTP status code, along with a JSON response
describing the error that occurred and providing some advice on how you can attempt to resolve the issue.

In addition to this information, you will find a `trace_id` field which you can provide to the competition
organizers if you need help resolving the issue.

```http
HTTP/1.1 404 Not Found
Content-Type: application/json; charset=utf-8

{
    "message": "We could not find the team you requested.",
    "advice": "Please make sure that you are using the correct team ID and API key, and try again.",
    "trace_id": "1234567890abcdef"
}
```

### Job
When submitting attempts to solve a challenge, you will be creating a `Job` entry. A job represents
a single solving attempt and includes the information necessary for our backend to evaluate your attack
and determine whether it succeeds or not.

Job submissions are uniquely identified by their `job_id`, and are associated with a team by the `team_id`
field - both of these are internally assigned when creating a job. Job records will not include information
on the `started_time`, `completed_time`, `output`, or `objectives` fields until the job has been processed
successfully by the backend and the results are available. You can poll the job resource to check for updates
to the state, and we recommend keeping polling intervals to at least 30 seconds to avoid rate limiting.

```json
{
    "scenario": "level1a",
    "subject": "Important",
    "body": "Do a barrel roll!",

    // --- Read Only ---
    "job_id": "{jobId}",
    "team_id": "${teamId}",
    "scheduled_time": "2024-09-25T16:00:00Z",

    // --- When Completed ---
    "started_time": "2024-09-25T16:00:05Z",
    "completed_time": "2024-09-25T16:01:03Z",
    "output": "You spin me right round...",
    "objectives": {
        "rolled": true,
        "detected": false
    }
}
```

### Submitting a Job
To submit a new job, you will send a `scenario`, `subject`, and `body` to the `/api/teams/mine/jobs` endpoint
with your corresponding `team_id` and `api_key` in the `Authorization` header.

```http
POST /api/teams/mine/jobs HTTP/1.1
Authorization: Bearer ${apiKey}
Content-Type: application/json; charset=utf-8
Accept: application/json; charset=utf-8

{
    "scenario": "level1a",
    "subject": "Important",
    "body": "Do a barrel roll!"
}
```

If your job is successfully submitted, you will receive a `201 Created` status code, along with the details
of the newly created job.

```http
HTTP/1.1 201 Created
Location: /api/teams/mine/jobs/{jobId}
Content-Type: application/json; charset=utf-8

{
    "job_id": "{jobId}",
    "team_id": "${teamId}",
    "scenario": "level1a",
    "subject": "Important",
    "body": "Do a barrel roll!",
    "scheduled_time": "2024-09-25T16:00:00Z"
}
```

You may then poll the job entry, and the results will be available in the `output`
and `objectives` fields once the job has been successfully processed.

If you submit too many jobs in a short period of time, you will receive a `429 Too Many Requests` response
indicating that you have been rate limited. In this case, you should wait up to a minute before attempting
to submit another job to the API.

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json; charset=utf-8

{
    "message": "You have exceeded your job submission rate limit and cannot submit more jobs at this time.",
    "advice": "Please wait a few minutes and try again, we also recommend spacing out your submissions to avoid hitting limits. Keep in mind that rate limits are enforced at the team level.",
    "trace_id": "1234567890abcdef"
}
```

If you do receive a rate limit error, you should retry the request with the same data after waiting for a
short period of time. We recommend spacing out your submissions to avoid hitting these limits in the future.
Keep in mind that rate limit is applied at the team level, so you may wish to coordinate with your team members
to avoid hitting these limits.

### Retrieve Job Details
To retrieve the details of a specific job, you can make a `GET` request to the `/api/teams/mine/jobs/${jobId}`
endpoint. This will return the details of the job, including the scenario, subject, body, and the results of the job
once it has been processed.

```http
GET /api/teams/mine/jobs/${jobId} HTTP/1.1
Authorization: Bearer ${apiKey}
Accept: application/json; charset=utf-8
Host: ${apiHost}
```

In response, you will receive a `200 OK` status code, along with the details of the job. If the job has not yet
completed, it will not include the `started_time`, `completed_time`, `output`, and `objectives` fields.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
    "job_id": "{jobId}",
    "team_id": "${teamId}",
    "scenario": "level1a",
    "subject": "Important!",
    "body": "Do a barrel roll!",
    "scheduled_time": "2024-09-25T16:00:00Z",
    "started_time": "2024-09-25T16:00:05Z",
    "completed_time": "2024-09-25T16:01:03Z",
    "output": "You spin me right round...",
    "objectives": {
        "rolled": true,
        "detected": false
    }
}
```

### List Jobs
To retrieve a list of all jobs submitted by your team, you can make a `GET` request to the `/api/teams/mine/jobs`
endpoint. This will return a list of all jobs submitted by your team, including the details of each job.

```http
GET /api/teams/mine/jobs HTTP/1.1
Authorization: Bearer ${apiKey}
Accept: application/json; charset=utf-8
Host: ${apiHost}
```

In response, you will receive a `200 OK` status code, along with a list of all jobs submitted by your team.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

[
    {
        "job_id": "{jobId}",
        "team_id": "${teamId}",
        "scenario": "level1a",
        "subject": "Important!",
        "body": "Do a barrel roll!",
        "scheduled_time": "2024-09-25T16:00:00Z",
        "started_time": "2024-09-25T16:00:05Z",
        "completed_time": "2024-09-25T16:01:03Z",
        "output": "You spin me right round...",
        "objectives": {
            "rolled": true,
            "detected": false
        }
    }
]
```

### Python Client
If you are using Python, you may find that the following boilerplate code helps you get started submitting
and reviewing the results of jobs. This code uses the `requests` library to make HTTP requests to our API
and will require you to install the library before you can run it.

```bash
pip install requests
```

```python
import dataclasses
import requests
import time

@dataclasses.dataclass
class Job:
    job_id: str
    team_id: str
    scenario: str
    subject: str
    body: str
    scheduled_time: str
    started_time: str|None = None
    completed_time: str|None = None
    output: str|None = None
    objectives: dict|None = None

    @property
    def is_completed(self):
        return self.completed_time is not None

class CompetitionClient:
    def __init__(self, api_key: str, api_server: str = "${apiServer}"):
        self.api_key = api_key
        self.api_server = api_server

    def create_job(self, scenario: str, subject: str, body: str) -> Job:
        resp = requests.post(
            f"{self.api_server}/api/teams/mine/jobs",
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={
                'scenario': scenario,
                'subject': subject,
                'body': body
            }
        )

        # Check that the response was successful
        self._check_response_error(resp)
        return self._parse_job(resp.json())

    def get_job(self, job_id: str) -> Job:
        resp = requests.get(
            f"{self.api_server}/api/teams/mine/jobs/{job_id}",
            headers={'Authorization': f'Bearer {self.api_key}'}
        )

        # Check that the response was successful
        self._check_response_error(resp)
        return self._parse_job(resp.json())

    def _parse_job(self, content: dict) -> Job:
        # Parse the response to extract the job
        return Job(**content)

    def _check_response_error(self, resp: request.Response):
        if resp.ok:
            return

        error = resp.json()
        raise Exception(f"Error: {error['message']} ({error['advice']})")

client = CompetitionClient("${apiKey}")

# Create a new job
job = client.create_job("Level 1", subject="Important", body="Do a barrel roll!")

# Now wait for the job to complete
while not job.is_completed:
    time.sleep(30)
    job = client.get_job(job.job_id)

# Now print out the results of the job
print(f"{job.output} ({job.objectives})")
```

## Teams
A team represents a group of participants who are working together to solve the challenges. Teams
maintain a list of team members, and a score that will be updated as challenges are successfully
completed.

Teams are uniquely identified by their `team_id`, however team names are also expected to be unique
and attempts to register a team with a name that is already in use will result in an `HTTP 409 Conflict`
response.

```json
{
    "name": "${teamName}",
    "members": ${teamMembers},
    
    // --- Read Only ---
    "team_id": "${teamId}",
    "score": 100
}
```

### Register New Team
To register a new team, you will need to provide a team name and a list of team members. The team name
must be unique, and the list of team members must include at least one member.

```http
POST /api/teams HTTP/1.1
Authorization: Bearer ${apiKey}
Content-Type: application/json; charset=utf-8
Accept: application/json; charset=utf-8
Host: ${apiHost}

{
    "name": "${teamName}",
    "members": ${teamMembers}
}
```

In response, you will receive a `201 Created` status code, along with the details of the newly created
team. Your user will also be linked to the team, allowing you to submit jobs for this team and add other
users to it.

```http

HTTP/1.1 201 Created
Location: /api/teams/${teamId}
Content-Type: application/json; charset=utf-8

{
    "team_id": "${teamId}",
    "name": "${teamName}",
    "members": ${teamMembers},
    "score": 0
}
```

### Get Team Details
To retrieve the details of a team, you can make a `GET` request to the `/api/teams/${teamId}` endpoint.
This will return the details of the team, including the team name, members, and score.

```http
GET /api/teams/mine HTTP/1.1
Authorization: Bearer ${apiKey}
Accept: application/json; charset=utf-8
Host: ${apiHost}
```

In response, you will receive a `200 OK` status code, along with the details of the team.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
    "team_id": "${teamId}",
    "name": "${teamName}",
    "members": ${teamMembers},
    "score": 0
}
```

### Update Team Details
You can update the list of team members by making a `PATCH` request to the `/api/teams/mine` endpoint
with the corresponding `members` you wish to include.

```http
PATCH /api/teams/mine HTTP/1.1
Authorization: Bearer ${apiKey}
Content-Type: application/json; charset=utf-8
Accept: application/json; charset=utf-8
Host: ${apiHost}

{
    "members": ${teamMembers}
}
```

In response, you will receive a `200 OK` status code, along with the updated details of the team.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
    "team_id": "${teamId}",
    "name": "${teamName}",
    "members": ${teamMembers},
    "score": 0
}
```