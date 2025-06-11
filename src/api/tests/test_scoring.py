from services import ScoringModel
from services.scoring import BasicScoringModelCutoff
from datetime import datetime, timezone, timedelta
from random import random

from models import Team


def to_time(order: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=order)).isoformat()


def assert_order(teams: list[Team], expected_order: list[str]):
    assert [team.name for team in teams] == [
        team.name if isinstance(team, Team) else team for team in expected_order
    ]


def is_monotonically_decreasing(lst):
    """
    Checks if a list is monotonically decreasing.
    """
    for i in range(1, len(lst)):
        if lst[i] >= lst[i - 1]:
            return False
    return True


def is_same_value(lst):
    """
    Checks if a list has same values
    """
    prev_value = lst[0]
    for i in range(1, len(lst)):
        if lst[i] != prev_value:
            return False
    return True


def shuffled(teams: list[Team]) -> list[Team]:
    return sorted(teams, key=lambda team: random())


class ScoringModelHarness:
    model: ScoringModel

    def test_no_teams(self):
        """
        This ensures that the service doesn't crash when attempting to order an empty list of teams.
        """
        assert_order(self.model.order([]), [])

    def test_team_with_no_solutions(self):
        """
        This ensures that the service doesn't crash when attempting to order a team with no solutions.
        """
        team = Team("team1")
        assert_order(self.model.order([team]), ["team1"])

    def test_single_team(self):
        """
        This just ensures that the algorithm can handle cases where only one team is provided.
        """

        team = Team(
            "team1",
            solution_details={
                "level1a": to_time(1),
                "level2a": to_time(2),
            },
        )

        assert_order(self.model.order([team]), ["team1"])

    def test_first_solution_wins(self):
        """
        It MUST grant points for a problem such that subsequent solves provide teams with fewer points
        than prior solves (i.e. first to solve beats second, beats third, etc)

        This test ensures that the first team to solve a scenario will always be ranked higher than the second team.
        """

        team1 = Team(
            "team1",
            solution_details={
                "level1k": to_time(1),
            },
        )

        team2 = Team(
            "team2",
            solution_details={
                "level1k": to_time(2),
            },
        )

        assert_order(self.model.order([team1, team2]), [team1, team2])
        assert_order(self.model.order([team2, team1]), [team1, team2])

    def test_relative_solution_ordering(self):
        """
        It MUST grant points for a problem such that subsequent solves provide teams with fewer points
        than prior solves (i.e. first to solve beats second, beats third, etc)

        This test is a more complex version of the above test, validating that the same behaviour holds
        for larger pools of teams.
        """
        teams = [
            Team(
                f"team{i}",
                solution_details={
                    "level1k": to_time(i),
                },
            )
            for i in range(1, 6)
        ]

        assert_order(self.model.order(shuffled(teams)), teams)

    def test_hardest_scenario_wins(self):
        """
        It MUST grant more points for solving more difficult problems than for less difficult problems
        (i.e. problems which every team can solve should be worth less than those that only a small number
        of teams can solve).

        This tests that three teams, two of which have solved two scenarios in 1st and 2nd place, will
        have the team that solved the hardest scenario win (by having a 3rd team solve the outstanding scenario)
        """

        teams = [
            Team(
                "team1",
                solution_details={
                    "level1k": to_time(1),
                    "level1l": to_time(2),
                },
            ),
            Team(
                "team2",
                solution_details={
                    "level1k": to_time(1),
                    "level1l": to_time(2),
                },
            ),
            Team(
                "team3",
                solution_details={
                    "level2v": to_time(1),
                },
            ),
        ]

        assert_order(self.model.order(shuffled(teams)), teams)

    def test_unambiguous_submission_time_wins(self):
        """
        It MUST ensure that team placement is unambiguous for the top placing teams
        (i.e. no ties for any team eligible for a prize).

        This tests that two teams that have solved the same number of scenarios with the same difficulty
        will always be consistently ordered based on their average global submission ordering.
        """

        team1 = Team(
            "team1",
            solution_details={
                "level1k": to_time(1),
                "level2m": to_time(3),
            },
        )

        team2 = Team(
            "team2",
            solution_details={
                "level2k": to_time(2),
                "level1m": to_time(4),
            },
        )

        assert_order(self.model.order([team1, team2]), [team1, team2])
        assert_order(self.model.order([team2, team1]), [team1, team2])

    def test_unambiguous_first_50_teams(self):
        """
        This test generates 50 teams that all solve the same scenarios in a given order
        and ensures that for the first 50 teams the resulting order is deterministic (i.e.
        that the model does not decay to the point where teams in the top 50 have equivalent scores).
        """

        teams = [
            Team(
                f"team{i}",
                solution_details={
                    "level1k": to_time(i),
                },
            )
            for i in range(1, 51)
        ]

        assert_order(self.model.order(shuffled(teams)), teams)


class ScoringModelCutoffHarness(ScoringModelHarness):
    def test_order_saturation_after_threshold(self):
        """
        This test checks to ensure that the model does not overly penalize very late submission.
        Timestamp is a tie breaker
        The first 8 solutions will have monotonically decreasing scores, then the rest have fixed scores.
        """
        start_score = self.model.base_score
        min_score = self.model.min_decayed_score
        top_teams = 0
        while start_score > min_score:
            start_score *= self.model.order_multiplier
            top_teams += 1
        top_teams += 1

        teams_different_scores = [
            Team(
                f"team{i}",
                solution_details={
                    "level2k": to_time(i),
                },
            )
            for i in range(1, top_teams)
        ]

        teams_same_scores = [
            Team(
                f"team{i}",
                solution_details={
                    "level2k": to_time(i),
                },
            )
            for i in range(top_teams, top_teams + 10)
        ]

        assert_order(
            self.model.order(shuffled(teams_different_scores + teams_same_scores)),
            teams_different_scores + teams_same_scores,
        )
        assert is_monotonically_decreasing(self.model.team_score_sorted[0:top_teams]) and is_same_value(
            self.model.team_score_sorted[top_teams:]
        )


class TestBasicScoringModelCutOff(ScoringModelCutoffHarness):
    model = BasicScoringModelCutoff()
