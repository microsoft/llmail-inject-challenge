import os
from typing import List
from services.storage import STORAGE


def generate_levels(level_count: int, letters: List[str]) -> List[str]:
    levels = [f"level{i}{letter}" for i in range(1, level_count + 1) for letter in letters]
    return levels


def get_scenarios() -> List[str]:
    scenarios = STORAGE.storage.list_scenarios()
    if not scenarios:
        print("No scenarios retrieved from storage")
        return handle_no_scenarios()
    else:
        return [s.scenario_id for s in scenarios]


def handle_no_scenarios() -> List[str]:

    phase = int(os.getenv("COMPETITION_PHASE", 2))

    if phase == 1:
        return generate_levels(level_count=4, letters=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
    elif phase == 2:
        return generate_levels(
            level_count=2, letters=["k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v"]
        )
    else:
        raise ValueError(f"Invalid competition phase {phase} received")
