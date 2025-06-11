# Architecture

## Requirements
### Functional
 - User provides an email as input (plain body string)
 - One model per agent, with multiple defense implementations selected at runtime
 - LLM plugin which "sends an email" (target for attackers)

### Non Functional
 - Use Azure Functions 

## Flows

### Data Flows
```mermaid
flowchart LR
    user --> ui --> api
    user --> api

    api --> dispatch_queue --> agent --> llm

    api --> table

    agent --> result_queue --> api
```

### API Request Handling Workflow
```mermaid
sequenceDiagram
    User ->> API: POST /api/teams/{team_id}/jobs

    critical Validate API Key
        API ->> APIKeys Table: Fetch entry for API key in Authorization header
        API -->> User: Return 401 Unauthorized if not found
        APIKeys Table -->> API: Team ID
        Note over API: Check that Team ID matches the Team ID in the URL
        API -->> User: Return 403 Forbidden if not matching
    end

    critical Schedule Job
        API ->> Jobs Table: Create $JobRecord
        Jobs Table -->> API: 201 Created

        API ->> Dispatch Queue: Schedule $JobMessage
        Dispatch Queue -->> API: 201 Created
    end

    API -->> User: 202 Accepted (Location: /api/teams/{team_id}/jobs/{job_id})
```

### Submission Workflow
```mermaid
sequenceDiagram
    User ->> API: Email Content
    activate API
    API -->> User: 202 Accepted (Location: /jobs/{id})

    API ->> Table Storage: Initial $JobRecord
    activate Dispatch Queue
    API ->> Dispatch Queue: $JobMessage
    deactivate API

    loop Forever
        API ->> Result Queue: Poll for results
        Result Queue -->> API: $JobResult
        API ->> Table Storage: Update $JobRecord based on $JobResult
    end

    loop Forever
        Agent ->> Dispatch Queue: Poll for work
        Dispatch Queue -->> Agent: $JobMessage
        deactivate Dispatch Queue
        activate Agent
        Agent ->> LLM: Run LLM task and evaluate performance
        Agent ->> Result Queue: $JobResult
        deactivate Agent
    end
```

### System Design
```mermaid
flowchart TB
    subgraph API Azure Functions
        api_get_jobs[/"GET /api/teams/{team_id}/jobs"/] --> azfn_http[Azure Function HTTP Trigger]
        api_post_jobs[/"POST /api/teams/{team_id}"/] --> azfn_http
        api_get_job[/"GET /api/teams/{team_id}/job/{id}"/] --> azfn_http
    end

    subgraph Storage Account
        azfn_http --> storage_apikey[("Table Storage (APIKeys)")]
        azfn_http --> storage_teams[("Table Storage (Teams)")]
        azfn_http --> storage_jobs[("Table Storage (Jobs)")]
        azfn_http --> queue_dispatch[("Queue Storage (dispatch_{model})")]
        azfn_http --> queue_results[("Queue Storage (results)")]
    end

    subgraph "Agent Container(s)"
        agent[Agent] --> queue_dispatch
        agent --> queue_results

        agent --> defense["Defense Layer(s)"] --> LLM
        LLM -.-> agent

        acr[(Container Registry)] --> agent
    end

    subgraph Results Azure Function
        queue_results --> azfn_queue["Azure Function Queue Trigger"] --> storage_jobs
    end
    
```

## API Methods

### `GET /api/teams/{team_id}/jobs`
```http
GET /api/teams/00000000-0000-0000-0000-000000000000/jobs HTTP/1.1
Authorization: Bearer <api-key>
```

```http
200 OK HTTP/1.1
Content-Type: application/json

[
    {
        "id": "00000000-0000-0000-0000-000000000000",
        "team_id": "00000000-0000-0000-0000-000000000000",
        "scheduled_time": "2024-09-07T15:23:00Z",
        "started_time": "2024-09-07T15:25:00Z",
        "completed_time": "2024-09-07T15:29:00Z",
        "model": "Llama3",
        "context": {
            "defense": "TaskTracker",
            "scenario": "Level 1"
        }
        "prompt": "...",
        "output": "...",
        "objectives": {
            "detector": true,
            "email": false
        }
    }
]
```

### `POST /api/teams/{team_id}/jobs`
```http
POST /api/teams/00000000-0000-0000-0000-000000000000/jobs HTTP/1.1
Content-Type: application/json
Authorization: Bearer <api-key>

{
    "model": "Llama3",
    "context": {
        "defense": "TaskTracker",
        "scenario": "Level 1"
    },
    "prompt": "..."
}
```

```http
202 Accepted HTTP/1.1
Location: /api/teams/00000000-0000-0000-0000-000000000000/jobs/00000000-0000-0000-0000-000000000000
```

### `GET /api/teams/{team_id}/jobs/{id}`
```http
GET /api/teams/00000000-0000-0000-0000-000000000000/jobs/00000000-0000-0000-0000-000000000000 HTTP/1.1
Authorization: Bearer <api-key>
```

```http
200 OK HTTP/1.1
Content-Type: application/json

{
    "id": "00000000-0000-0000-0000-000000000000",
    "team_id": "00000000-0000-0000-0000-000000000000",
    "scheduled_time": "2024-09-07T15:23:00Z",
    "started_time": "2024-09-07T15:25:00Z",
    "completed_time": "2024-09-07T15:29:00Z",
    "model": "Llama3",
    "context": {
        "defense": "TaskTracker",
        "scenario": "Level 1"
    }
    "prompt": "...",
    "output": "...",
    "objectives": {
        "detector": true,
        "email": false
    }
}
```

## Schemas

### Team
Stored in Table Storage and used for rate limiting.
```json
{
    // RowKey
    "team_id": "00000000-0000-0000-0000-000000000000",
    "team_name": "HackerZ",
    "members": ["Alice", "Bob"],
    "rate_limit_watermark": "2024-09-07T15:00:00Z",
    "score": 100
}
```

### APIKey
Stored in Table Storage and used to check authentication.

```json
{
    // RowKey
    "api_key": "00000000-0000-0000-0000-000000000000",
    "team_id": "00000000-0000-0000-0000-000000000000"
}
```

### JobMessage
Sent by the API to a queue called `dispatch_${model}` and picked up by the agent.

```json
{
    // Partition Key
    "team_id": "00000000-0000-0000-0000-000000000000",
    // Sort Key/Row Key
    "id": "00000000-0000-0000-0000-000000000000",
    "model": "Llama3",
    "context": {
        "defense": "TaskTracker",
        "scenario": "Level 1"
    },
    "prompt": "..."
}
```

### JobResult
Sent by the agent to a queue called `results`

```json
{
    // Partition Key
    "team_id": "00000000-0000-0000-0000-000000000000",
    // Sort Key/Row Key
    "id": "00000000-0000-0000-0000-000000000000",
    "started_time": "2024-09-07T15:25:00Z",
    "completed_time": "2024-09-07T15:29:00Z",
    "output": "...",
    "objectives": {
        "detector": true,
        "email": false
    }
}
```

### JobRecord
```json
{
    // Partition Key
    "team_id": "00000000-0000-0000-0000-000000000000",
    // Sort Key/Row Key
    "id": "00000000-0000-0000-0000-000000000000",
    "scheduled_time": "2024-09-07T15:23:00Z",
    "started_time": "2024-09-07T15:25:00Z",
    "completed_time": "2024-09-07T15:29:00Z",
    "model": "Llama3",
    "context": {
        "defense": "TaskTracker",
        "scenario": "Level 1"
    },
    "prompt": "...",
    "output": "...",
    "objectives": {
        "detector": true,
        "email": false
    }
}
```

## Code Interfaces

```python
from abc import ABC

class Agent(ABC):
    def __init__(self, workload: AgentWorkload):
        self.workload = workload

    async def run(self):
        while True:
            job = await self.get_next_job()
            result = await self.workload.execute(job)
            await self.handle_result(result)


    @abstract
    async def get_next_job(self) -> JobMessage:
        pass

    @abstract
    async def handle_result(self, result: JobResult):
        pass

class LocalTestAgent(Agent):
    """
    Allows an agent workload to be executed from the command line (without a queue)
    """
    
    async def get_next_job(self):
        return new JobMessage(
            # From command line args/json file
        )

    async def handle_result(self, result: JobResult):
        print(repr(result))
        raise Exception("Execution has completed")

class AzureQueueAgent(Agent):
    pass

class Llama3Email(AgentWorkload):
    def __init__(self):
        super().__init__(self, "llama3")

    async def execute(self, job: JobMessage) -> JobResult:
        # Run the Llama3 model for this challenge and score the results
        return JobResult(...)

class AgentWorkload(ABC):
    def __init__(self, kind: string):
        self.kind = kind

    @abstract
    async def execute(self, job: JobMessage) -> JobResult:
        pass

class JobMessage:
    def build_result(self, output: string, ...) -> JobResult:
        pass

class JobResult:
    pass
```