import azure.functions as func
import json
import logging
import urllib.parse
import os

from models import to_api
from .mixins import authenticated, instrumented, error_handler
from services import STORAGE

scenarios = func.Blueprint()
competition_phase = int(os.getenv("COMPETITION_PHASE", 2))


@scenarios.route("api/scenarios", methods=["GET"])
@error_handler
@instrumented("/api/scenarios")
async def scenarios_list(req: func.HttpRequest) -> func.HttpResponse:
    scenarios = STORAGE.storage.list_scenarios()

    return func.HttpResponse(
        json.dumps([to_api(scenario) for scenario in scenarios]),
        status_code=200,
        mimetype="application/json",
    )
