from datetime import datetime
from dataclasses import dataclass, field
import uuid


@dataclass
class Team:
    name: str
    team_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    members: list[str] = field(default_factory=list)
    solved_scenarios: list[str] = field(default_factory=list)
    deleted: bool = False

    ### Internal fields ###
    # The timestamp when each scenario was solved by this team
    solution_details: dict[str, str] = field(default_factory=dict)
    rate_limit_watermark: float | None = None
    rate_limit_sustained: float | None = None
    rate_limit_burst: int | None = None
    rate_limit_total: int | None = None
    rate_limit_counter: int = 0
    is_enabled: bool = True

    __json_fields__ = ["members", "solved_scenarios", "solution_details"]

    __api_fields__ = ["team_id", "name", "members", "score", "is_enabled", "solved_scenarios"]

    def partition_key(self):
        return self.team_id

    def row_key(self):
        return self.team_id

    def update_rate_limit_watermark(self, new_watermark: datetime):
        """
        Updates the rate limit watermark with a new timestamp.
        """
        self.rate_limit_watermark = new_watermark.timestamp()

    def enable_team(self) -> None:
        """
        Enables the team.
        """
        self.is_enabled = True

    def disable_team(self) -> None:
        """
        Disables the team. This is the default state when the team is created.
        """
        self.is_enabled = False
