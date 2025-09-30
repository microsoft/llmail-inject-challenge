import json
import azure.functions as func
import logging

from .mixins import instrumented, error_handler
from services import STORAGE, ScoringModel
from services.scoring import BasicScoringModelCutoff
from models import to_api, Leaderboard

leaderboard_api = func.Blueprint()


@leaderboard_api.route("api/leaderboard", methods=["GET"])
@error_handler
@instrumented("/api/leaderboard")
async def leaderboard_get(req: func.HttpRequest) -> func.HttpResponse:
    leaderboard = STORAGE.storage.get_leaderboard()

    return func.HttpResponse(
        json.dumps(to_api(leaderboard)),
        status_code=200,
        mimetype="application/json",
    )


@leaderboard_api.timer_trigger("timer", "*/30 * * * * *", run_on_startup=True)
async def leaderboard_builder(timer: func.TimerRequest):
    teams = STORAGE.storage.list_teams()

    score_model: ScoringModel = BasicScoringModelCutoff()

    leaderboard = Leaderboard(
        teams=[team.team_id for team in score_model.order(teams) if not team.deleted],
    )

    STORAGE.storage.upsert_leaderboard(leaderboard)
