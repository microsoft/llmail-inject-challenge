from datetime import datetime, timezone
from dataclasses import dataclass, field
import os


@dataclass
class Leaderboard:
    teams: list[str]
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    __json_fields__ = ["teams"]

    __api_fields__ = ["teams", "last_updated"]

    def partition_key(self):
        return "leaderboard"

    def row_key(self):
        phase = int(os.getenv("COMPETITION_PHASE", 2))
        return f"leaderboard_phase{phase}"
