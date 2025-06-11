from authlib.integrations.requests_client import OAuth2Session
import azure.functions as func
import dataclasses
import json
import logging
import os
import requests
import urllib.parse

from models import User, to_api

from .mixins import authenticated, instrumented, error_handler
from .errors import error_response
from services import STORAGE

auth = func.Blueprint()

SIGNUP_ALLOWLIST = set([user.strip().lower() for user in os.getenv("SIGNUP_ALLOWLIST", "").split(",")])

github_auth_endpoint = "https://github.com/login/oauth/authorize"
github_token_endpoint = "https://github.com/login/oauth/access_token"
if "GITHUB_CLIENT_ID" not in os.environ:
    github_client = None
else:
    github_client = OAuth2Session(
        client_id=os.environ["GITHUB_CLIENT_ID"],
        client_secret=os.environ["GITHUB_CLIENT_SECRET"],
        redirect_uri=os.environ["GITHUB_REDIRECT_URI"],
    )


@auth.route("api/auth/login", methods=["GET"])
@error_handler
@instrumented("/api/auth/login")
async def auth_login(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        status_code=302,
        headers={"Location": _get_login_url()},
    )


@auth.route("api/auth/callback", methods=["GET"])
@error_handler
@instrumented("/api/auth/callback")
async def auth_callback(req: func.HttpRequest) -> func.HttpResponse:
    token = _get_access_token_from_redirect(req)

    user_info = _get_user_info(token)

    # When empty, the set has size 1 with an empty string.
    has_signup_allowlist = len(SIGNUP_ALLOWLIST) > 1

    user = STORAGE.storage.get_user(user_info.login)
    if user is None:
        user = User(
            login=user_info.login,
            blocked=has_signup_allowlist and user_info.login not in SIGNUP_ALLOWLIST,
        )
        STORAGE.storage.upsert_user(user)

    if user.blocked:
        return error_response(
            403,
            "The competition hasn't started yet.",
            "Please, monitor https://llmailinject.azurewebsites.net/ for updates on the start date. Thank you for your patience",
        )

    return func.HttpResponse(
        status_code=302,
        headers={
            "Location": "/",
            "Set-Cookie": f"Auth={user.auth_token()}; HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=86400",
        },
    )


@auth.route("api/auth/me", methods=["GET"])
@error_handler
@instrumented("/api/auth/me")
@authenticated
async def auth_me(req: func.HttpRequest, user: User) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({**to_api(user), "api_key": user.auth_token()}),
        status_code=200,
        mimetype="application/json",
    )


@auth.route("api/auth/logout", methods=["GET"])
@error_handler
@instrumented("/api/auth/logout")
@authenticated
async def auth_logout(req: func.HttpRequest, user: User) -> func.HttpResponse:
    return func.HttpResponse(
        status_code=302,
        headers={
            "Location": "/",
            "Set-Cookie": "Auth=; HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=0",
        },
    )


@auth.route("api/auth/rotate-key", methods=["POST"])
@error_handler
@instrumented("/api/auth/rotate-key")
@authenticated
async def auth_rotate_key(req: func.HttpRequest, user: User) -> func.HttpResponse:
    user.rotate_auth_token()
    STORAGE.storage.upsert_user(user)

    return func.HttpResponse(
        json.dumps({**to_api(user), "api_key": user.auth_token()}),
        status_code=200,
        mimetype="application/json",
        headers={
            "Set-Cookie": f"Auth={user.auth_token()}; HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=86400",
        },
    )


@dataclasses.dataclass
class AccessToken:
    access_token: str
    token_type: str
    scope: str


@dataclasses.dataclass
class UserInfo:
    login: str
    name: str


def _get_login_url() -> str:
    if github_client is None:
        return "http://localhost:7071/api/auth/callback"

    uri, _state = github_client.create_authorization_url(github_auth_endpoint)
    return uri


def _get_access_token_from_redirect(req: func.HttpRequest) -> AccessToken:
    if github_client is None:
        return AccessToken(
            access_token="test-token",
            token_type="bearer",
            scope="",
        )

    access_token = github_client.fetch_token(
        github_token_endpoint,
        authorization_response=req.url,
    )

    return AccessToken(
        **{
            k: v
            for k, v in access_token.items()
            if k in AccessToken.__dataclass_fields__  
    )


def _get_user_info(access_token: AccessToken) -> UserInfo:
    if github_client is None:
        return UserInfo(
            login="test-user",
            name="Test User",
        )

    user = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"{access_token.token_type} {access_token.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ).json()

    return UserInfo(
        login=user["login"].lower(),
        name=user["name"],
    )
