from dataclasses import dataclass, asdict, field


@dataclass
class Scenario:
    scenario_id: str
    name: str
    description: str
    objectives: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    workqueue: str = "dispatch"
    solves: int = 0
    phase: int = 1

    __json_fields__ = [
        "metadata",
        "objectives",
    ]

    __api_fields__ = ["scenario_id", "name", "description", "objectives", "metadata", "solves", "phase"]

    def partition_key(self):
        return self.scenario_id

    def row_key(self):
        return self.scenario_id
