import azure.functions as func
import json
import logging
import urllib.parse

from models import User, Team, to_api

from .mixins import (
    authenticated,
    maybe_authenticated,
    require_team_membership,
    require_role,
    instrumented,
    error_handler,
)
from services import STORAGE
from .errors import error_response

TEAM_SIZE_LIMIT = 5

teams = func.Blueprint()


@teams.route("api/teams", methods=["GET"])
@error_handler
@instrumented("/api/teams")
@maybe_authenticated
async def teams_list(req: func.HttpRequest, user: User | None) -> func.HttpResponse:
    teams = STORAGE.storage.list_teams()

    return func.HttpResponse(
        json.dumps(
            [
                to_api(team, fields=["team_id", "name"] if user is None else None)
                for team in teams
                if not team.deleted
            ]
        ),
        status_code=200,
        mimetype="application/json",
    )


@teams.route("api/teams", methods=["POST"])
@error_handler
@instrumented("/api/teams")
@authenticated
async def teams_create(req: func.HttpRequest, user: User) -> func.HttpResponse:
    if user.team:
        return error_response(
            409,
            "You are already a member of a team and cannot create a new team.",
            "Please leave your current team before creating a new one.",
        )

    req_body = req.get_json()
    team_name = req_body.get("name")

    if not team_name:
        return error_response(
            400,
            "You did not provide a valid 'name' field in the request.",
            "Please make sure that you provide a valid team name in your request.",
        )

    if STORAGE.storage.get_team_by_name(team_name):
        logging.warning(f"Team with name '{team_name}' already exists.")

        return error_response(
            409,
            "The team name you provided has already been used by another team.",
            "Please choose a unique team name and try registering again.",
        )

    team = Team(team_name, members=[user.login])
    user.team = team.team_id

    STORAGE.storage.upsert_team(team)
    STORAGE.storage.upsert_user(user)

    logging.info(f"Team '{team_name}' created with ID: {team.team_id}")

    return func.HttpResponse(
        json.dumps(to_api(team)),
        status_code=201,
        mimetype="application/json",
        headers={"Location": f"/api/teams/{team.team_id}"},
    )


@teams.route("api/teams/{team_id}", methods=["GET"])
@error_handler
@instrumented("/api/teams/{team_id}")
@authenticated
async def team_get(req: func.HttpRequest, user: User) -> func.HttpResponse:
    """
    Retrieves team information from the Teams table by team_id.
    """
    team_id = req.route_params.get("team_id")

    if team_id == "mine":
        team_id = user.team

    if not team_id:
        return error_response(
            400,
            "Your request URL does not include valid team ID in the /api/teams/{team_id}/... portion of the request.",
            "Please make sure that you have filled in your team ID correctly when creating the URL, or if you are using /api/teams/mine/... ensure that you are a member of a team.",
        )

    team = STORAGE.storage.get_team(team_id)

    if team is None:
        logging.error(
            f"Team with ID {team_id} not found after passing auth check (unclean deletion of a team?)."
        )
        return error_response(
            404,
            "The team you attempted to retrieve information about does not exist.",
            "Please make sure that you are using the correct team ID and that you have permission to view this team's information.",
        )

    if team.deleted:
        return error_response(
            404,
            "The team you attempted to retrieve information about does not exist.",
            "Please make sure that you are using the correct team ID and that you have permission to view this team's information.",
        )

    logging.debug(f"Fetched team data for team_id: {team_id}")

    return func.HttpResponse(
        json.dumps(to_api(team)),
        status_code=200,
        mimetype="application/json",
    )


@teams.route("api/teams/{team_id}", methods=["PATCH"])
@error_handler
@instrumented("/api/teams/{team_id}")
@authenticated
@require_team_membership
async def team_update(req: func.HttpRequest, user: User) -> func.HttpResponse:
    """
    Updates the members of a team.
    """
    req_body = req.get_json()
    team_id = req.route_params.get("team_id")
    members = req_body.get("members")

    if team_id == "mine":
        team_id = user.team

    if not team_id or not members or not isinstance(members, list):
        return error_response(
            400,
            "You did not provide a valid 'members' field in the request.",
            "Please make sure that you provide a valid list of team members in your request.",
        )

    if members == []:
        return error_response(
            400,
            "You cannot remove all members from a team.",
            "Please make sure that you provide a valid list of team members in your request.",
        )

    return _update_team_members(team_id=team_id, members=members)


@teams.route("api/teams/{team_id}", methods=["DELETE"])
@error_handler
@instrumented("/api/teams/{team_id}")
@authenticated
@require_team_membership
async def team_delete(req: func.HttpRequest, user: User) -> func.HttpResponse:
    """
    Deletes a team if the current user is the last member of the team.
    """

    team_id = req.route_params.get("team_id")
    if team_id == "mine":
        team_id = user.team

    if not team_id:
        return error_response(
            400,
            "You cannot delete a team if you are not a member of one.",
            "Make sure that you are a member of the team you are planning to delete.",
        )

    team = STORAGE.storage.get_team(team_id)
    if team is None:
        return error_response(
            404,
            f"Team with ID {team_id} not found.",
            "Please make sure that you are using the correct team ID.",
        )

    if len(team.members) > 1:
        return error_response(
            409,
            "You cannot delete a team if there are other team members in it.",
            "Make sure that you are the last member of the team before deleting it.",
        )

    for member in team.members:
        team_user = STORAGE.storage.get_user(member)
        if team_user is not None:
            logging.debug(f"Marking user {member} as not being in a team.")
            team_user.team = None
            STORAGE.storage.upsert_user(team_user)

    logging.debug(f"Marking team '{team_id}' as deleted.")
    team.deleted = True
    team.is_enabled = False
    team.members = []
    STORAGE.storage.upsert_team(team)

    return func.HttpResponse(
        status_code=204,
    )


@teams.route("api/teams/{team_id}/enable", methods=["POST"])
@error_handler
@instrumented("/api/teams/{team_id}/enable")
@authenticated
@require_role("admin")
async def team_enable(req: func.HttpRequest, user: User) -> func.HttpResponse:
    """
    Enable a team to submit jobs.
    """
    team_id = req.route_params.get("team_id")

    team: Team | None = None
    if team_id is not None:
        team = STORAGE.storage.get_team(team_id)
    if team_id is None or team is None:
        logging.warning(f"Team with ID {team_id} not found.")
        return error_response(
            404,
            f"Team with ID {team_id} not found.",
            "Please make sure that you are using the correct team ID.",
        )

    team.enable_team()
    STORAGE.storage.upsert_team(team)

    return func.HttpResponse(
        json.dumps(to_api(team)),
        status_code=200,
        mimetype="application/json",
    )


@teams.route("api/teams/{team_id}/disable", methods=["POST"])
@error_handler
@instrumented("/api/teams/{team_id}/disable")
@authenticated
@require_role("admin")
async def team_disable(req: func.HttpRequest, user: User) -> func.HttpResponse:
    """
    Disable a team, they can not submit jobs.
    """
    team_id = req.route_params.get("team_id")

    team: Team | None = None
    if team_id is not None:
        team = STORAGE.storage.get_team(team_id)
    if team_id is None or team is None:
        logging.warning(f"Team with ID {team_id} not found.")
        return error_response(
            404,
            f"Team with ID {team_id} not found.",
            "Please make sure that you are using the correct team ID.",
        )

    team.disable_team()
    STORAGE.storage.upsert_team(team)

    return func.HttpResponse(
        json.dumps(to_api(team)),
        status_code=200,
        mimetype="application/json",
    )


def _update_team_members(team_id: str, members: list) -> func.HttpResponse:
    """
    Adds a new member to an existing team in Azure Table REPOS.storage.
    """
    team = STORAGE.storage.get_team(team_id)
    if team is None:
        logging.warning(f"Team with ID {team_id} not found.")
        return error_response(
            404,
            f"Team with ID {team_id} not found.",
            "Please make sure that you are using the correct team ID.",
        )

    if team.deleted:
        logging.warning(f"Team with ID {team_id} is deleted.")
        return error_response(
            404,
            f"Team with ID {team_id} not found.",
            "Please make sure that you are using the correct team ID.",
        )

    # Check if the team is at capacity before adding a new member
    if len(members) > TEAM_SIZE_LIMIT:
        return error_response(
            409,
            f"Team with ID {team_id} would exceed the maximum team size of 5 members.",
            "Please create a new team, or remove members who are no longer active.",
        )

    existing_members = team.members
    new_members = set(members) - set(existing_members)
    removed_members = set(existing_members) - set(members)

    for member in new_members:
        logging.info(f"Adding user {member} to team {team_id}.")
        new_user = STORAGE.storage.get_user(member.lower())

        if new_user is None:
            logging.warning(f"User {member} not found.")
            return error_response(
                404,
                f"We could not find a registered user with the GitHub username '{member}'.",
                "Please make sure that the person you are trying to add has already signed up for the competition.",
            )

        if new_user.team is not None and new_user.team != team_id:
            logging.warning(f"User {member} is already a member of another team ({new_user.team}).")
            return error_response(
                409,
                f"{member} is already a member of another team and cannot be added to this one.",
                "The user will need to leave their current team before they can join this team.",
            )

        new_user.team = team_id
        STORAGE.storage.upsert_user(new_user)

        team.members.append(member.lower())

    for member in removed_members:
        logging.info(f"Removing user {member} from team {team_id}.")
        removed_user = STORAGE.storage.get_user(member)
        if removed_user is not None:
            removed_user.team = None
            STORAGE.storage.upsert_user(removed_user)

        team.members.remove(member)

    STORAGE.storage.upsert_team(team)

    logging.debug(f"Updated team members for team {team_id} to be {members}.")

    return func.HttpResponse(
        json.dumps(to_api(team)),
        status_code=200,
        mimetype="application/json",
    )
