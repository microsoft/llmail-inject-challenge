from abc import abstractmethod, ABC
from collections import defaultdict
from datetime import datetime
from typing import List
import os
from models.team import Team
from .scenarios import get_scenarios


class ScoringModel(ABC):
    """
    A scoring model is responsible for ordering teams based on their performance in the competition.

    It is required to implement the `order` method, which takes a list of teams and returns a list of teams
    ordered by their relative performance. This output is required to meet the following criteria:

     - It MUST ensure that team placement is unambiguous for the top placing teams (i.e. no ties for any team eligible for a prize).
     - It MUST grant points for a problem such that subsequent solves provide teams with fewer points than prior solves (i.e. first to solve beats second, beats third, etc)
     - It MUST grant more points for solving more difficult problems than for less difficult problems (i.e. problems which every team can solve should be worth less than those that only a small number of teams can solve).
     - It MUST be resilient to race conditions (i.e. it should not be possible for two teams solving a problem at near the same instant to get the same score).
     - It SHOULD be implemented in a way that ensures the implementation is provable, durable, and deterministic.
     - It SHOULD be implemented in a manner which allows post-facto auditing of scores to verify the outcome.
    """

    @abstractmethod
    def order(self, teams: List[Team]) -> List[Team]:
        pass


class BasicScoringModelCutoff(ScoringModel):
    """
    A basic scoring model that orders teams based on three factors:
     - The order in which they solve a scenario (First few teams will get higher scores than it saturates)
     - The difficulty of each scenario (based on the number of teams which successfully solve it)
     - The average point in time when the team solved their scenarios (for tie breaking)

    ## Parameters
    :param base_score:
        The base score for solving a scenario if you are the first and only team to solve it.

    :param min_decayed_score:
        The min score that decaying will result in (a lower bound for how decaying could penalize teams)

    :param difficulty_multiplier:
        A multiplier applied to the base score for all teams each time a new team solves the scenario.
        This value must be on the range (0..1) and higher values result in less penalization for scenarios
        which are solved by many teams.

    :param order_multiplier:
        A multiplier applied to the base score for a team based on the order in which they solved the scenario.
        This value must be on the range (0..1) and higher values result in less penalization for teams which
        solve the scenario later.
    """

    def __init__(
        self,
        base_score: int = 40000,
        min_decayed_score: int = 30000,
        difficulty_multiplier: float = 0.85,
        order_multiplier: float = 0.95,
    ):

        self.base_score = base_score
        self.difficulty_multiplier = difficulty_multiplier
        self.order_multiplier = order_multiplier
        self.min_decayed_score = min_decayed_score

    def order(self, teams: List[Team]) -> List[Team]:
        level_solves: defaultdict[str, int] = defaultdict(lambda: 0)
        level_times: defaultdict[str, List[datetime]] = defaultdict(list)
        avg_solve_time: defaultdict[str, float] = defaultdict(lambda: 0)

        team_solved_scenarios_map = {}
        for team in teams:
            # Skip teams that have not solved any scenarios
            if len(team.solution_details) == 0:
                team_solved_scenarios_map[team.team_id] = []
                continue

            valid_scenarios = get_scenarios()

            solved_scenarios = [
                (scenario, timestamp)
                for scenario, timestamp in team.solution_details.items()
                if scenario in valid_scenarios
            ]
            solve_time_sum = 0.0
            for scenario, timestamp_str in solved_scenarios:
                dt = datetime.fromisoformat(timestamp_str)
                level_solves[scenario] += 1
                level_times[scenario].append(dt)
                solve_time_sum += dt.timestamp()

            # We calculate the average point in time when the team solved their scenarios
            # (i.e. the point where if they solved all scenarios at once, it would have the same center
            # of mass as the actual solve times).
            # THis gives us a way to break ties between teams with the same score by relying on a true
            # global ordering of submissions, and avoids biasing for first submission.
            if solved_scenarios:
                avg_solve_time[team.team_id] = solve_time_sum / len(solved_scenarios)
            else:
                avg_solve_time[team.team_id] = 0.0
            team_solved_scenarios_map[team.team_id] = solved_scenarios

        for scenario in level_times:
            level_times[scenario].sort()

        team_score: dict[str, float] = defaultdict(lambda: 0)
        for team in teams:
            solved_scenarios = team_solved_scenarios_map.get(team.team_id, [])
            for scenario, timestamp_str in solved_scenarios:

                dt = datetime.fromisoformat(timestamp_str)
                # We start with a base score for all levels
                score: float = self.base_score
                # And we adjust the score down further based on the order in which a given team solved it
                score *= self.order_multiplier ** level_times[scenario].index(dt)
                # The minimum score that can be achieved after decay is self.min_decayed_score
                score = max(self.min_decayed_score, score)
                # We then adjust the score down based on the number of teams who have solved it
                score *= self.difficulty_multiplier ** (level_solves[scenario] - 1)

                # This score is then added to the team's total internal score
                team_score[team.team_id] += score

        self.team_score_sorted = list(team_score.values())
        self.team_score_sorted.sort(reverse=True)

        return sorted(
            teams,
            # The order of teams is determined by their score, and in the case of ties we use the average solve time
            key=lambda team: (team_score[team.team_id], -avg_solve_time[team.team_id]),
            reverse=True,
        )
