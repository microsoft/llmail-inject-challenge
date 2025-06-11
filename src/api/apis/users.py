import azure.functions as func
import json
import logging
import urllib.parse

from models import User, to_api

from .mixins import authenticated, instrumented, error_handler, require_role
from services import STORAGE
from .errors import error_response

users = func.Blueprint()


@users.route("api/users", methods=["GET"])
@error_handler
@instrumented("/api/users")
@authenticated
@require_role("admin")
async def users_list(req: func.HttpRequest, me: User) -> func.HttpResponse:
    users = STORAGE.storage.list_users()

    return func.HttpResponse(
        json.dumps([to_api(user) for user in users]),
        status_code=200,
        mimetype="application/json",
    )


@users.route("api/users/{login}", methods=["GET"])
@error_handler
@instrumented("/api/users/{login}")
@authenticated
@require_role("admin")
async def users_get(req: func.HttpRequest, me: User, login: str) -> func.HttpResponse:
    user = STORAGE.storage.get_user(login)

    if user is None:
        return error_response(
            404,
            f"User with login '{login}' not found.",
            "Make sure that the user has been registered before attempting to retrieve their account information",
        )

    return func.HttpResponse(
        json.dumps(to_api(user)),
        status_code=200,
        mimetype="application/json",
    )


@users.route("api/users/{login}", methods=["DELETE"])
@error_handler
@instrumented("/api/users/{login}")
@authenticated
@require_role("admin")
async def users_delete(req: func.HttpRequest, me: User, login: str) -> func.HttpResponse:
    user = STORAGE.storage.get_user(login)

    if user is None:
        return error_response(
            404,
            f"User with login '{login}' not found.",
            "Make sure that the user has been registered before attempting to delete their account.",
        )

    STORAGE.storage.delete_user(user)

    return func.HttpResponse(
        status_code=204,
    )


@users.route("api/users/{login}", methods=["PATCH"])
@error_handler
@instrumented("/api/users/{login}")
@authenticated
@require_role("admin")
async def users_update(req: func.HttpRequest, me: User, login: str) -> func.HttpResponse:
    user = STORAGE.storage.get_user(login)

    if user is None:
        return error_response(
            404,
            f"User with login '{login}' not found.",
            "Make sure that the user has been registered before attempting to update their account information.",
        )

    req_body = req.get_json()

    if "role" in req_body:
        user.role = req_body["role"]

        if user.role not in ["admin", "competitor"]:
            return error_response(
                400,
                "You did not provide a valid 'role' field in the request.",
                "Please make sure that you provide a valid role in your request (either 'admin' or 'competitor').",
            )

    if "banned" in req_body:
        user.blocked = req_body["blocked"]

        if not isinstance(user.blocked, bool):
            return error_response(
                400,
                "You did not provide a valid 'banned' field in the request.",
                "Please make sure that you provide a valid boolean value to configure whether a user account is banned or not.",
            )

    STORAGE.storage.upsert_user(user)

    return func.HttpResponse(
        json.dumps(to_api(user)),
        status_code=200,
        mimetype="application/json",
    )
