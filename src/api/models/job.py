from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import uuid

from opentelemetry import trace, propagate, context


def _build_trace_context() -> dict:
    trace_context: dict[str, str] = {}

    propagate.inject(trace_context)
    return trace_context


@dataclass
class JobRecord:
    team_id: str
    scenario: str
    subject: str
    body: str
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scheduled_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_time: str | None = None
    completed_time: str | None = None
    output: str | None = None
    objectives: dict[str, bool] = field(default_factory=dict)

    __json_fields__ = ["context", "objectives"]

    __api_fields__ = [
        "team_id",
        "job_id",
        "scenario",
        "subject",
        "body",
        "output",
        "objectives",
        "scheduled_time",
        "started_time",
        "completed_time",
    ]

    def partition_key(self):
        return self.team_id

    def row_key(self):
        return self.job_id

    def to_dict(self):
        return asdict(self)

    def build_message(self) -> "JobMessage":
        return JobMessage(
            team_id=self.team_id,
            job_id=self.job_id,
            scenario=self.scenario,
            subject=self.subject,
            body=self.body,
            trace_context=_build_trace_context(),
        )

    def __str__(self):
        return f"{self.scenario} (team:{self.team_id}, job:{self.job_id})"


@dataclass
class JobMessage:
    team_id: str
    job_id: str
    scenario: str
    subject: str
    body: str

    trace_context: dict | None = field(default_factory=_build_trace_context)

    _internal_data: dict = field(default_factory=dict)

    __api_fields__ = [
        "team_id",
        "job_id",
        "scenario",
        "subject",
        "body",
        "trace_context",
    ]

    def get_trace_context(self) -> propagate.Context:
        if self.trace_context is None:
            return context.get_current()
        return propagate.extract(self.trace_context)

    def build_result(
        self,
        output: str,
        started_time: datetime | None = None,
        completed_time: datetime | None = None,
        **kwargs,
    ) -> "JobResult":
        objectives = kwargs.get("objectives", {})
        return JobResult(
            job_id=self.job_id,
            team_id=self.team_id,
            started_time=(started_time or datetime.now(timezone.utc)).isoformat(),
            completed_time=(completed_time or datetime.now(timezone.utc)).isoformat(),
            output=output,
            objectives=objectives,
            _internal_data=self._internal_data,
        )

    def __str__(self):
        return f"{self.scenario} (team:{self.team_id}, job:{self.job_id})"


@dataclass
class JobResult:
    team_id: str
    job_id: str
    started_time: str
    completed_time: str
    output: str
    objectives: dict[str, bool] | None = field(default_factory=dict)

    trace_context: dict = field(default_factory=_build_trace_context)

    _internal_data: dict = field(default_factory=dict)

    __api_fields__ = [
        "team_id",
        "job_id",
        "started_time",
        "completed_time",
        "output",
        "objectives",
        "trace_context",
    ]

    def get_trace_context(self) -> propagate.Context:
        if self.trace_context is None:
            return context.get_current()
        return propagate.extract(self.trace_context)

    def __str__(self):
        return self.job_id
