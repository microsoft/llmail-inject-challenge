import azure.functions as func
from typing import Callable, Awaitable

from models import User
from apis.errors import not_authorized, error_response


def require_team_membership(handler: Callable[[func.HttpRequest, User], Awaitable[func.HttpResponse]]):
    """
    Ensures that the authenticated user is a member of the team specified in the URL path. If the team ID is
    'mine', it will use the team ID from the authenticated user object. If the user is not a member of the team
    or is not an admin, it will return a 403 Forbidden error.

    This method is intended to be used in conjunction with the @authenticated decorator, and must always be
    applied after the @authenticated decorator in the handler chain.

    :param handler:
        The handler function to call if the user is a member of the team. This handler must be an async function
        and must accept two parameters: the incoming func.HttpRequest object and the authenticated model.User object.

    Example usage::

        @authenticated
        @require_team_membership
        async def main(req: func.HttpRequest, user: User) -> func.HttpResponse:
            return func.HttpResponse(f"Hello, {user.login
    """

    async def __wrapper(req: func.HttpRequest, user: User):
        team_id = req.route_params.get("team_id")
        if team_id == "mine":
            team_id = user.team

        if team_id is None:
            return error_response(
                400,
                "Your request URL does not include a valid team ID in the /api/teams/{team_id}/... portion of the request.",
                "Please make sure that you have filled in your team ID correctly when creating the URL, or if you are using /api/teams/mine/... ensure that you are a member of a team.",
            )

        if user.team != team_id and user.role != "admin":
            return not_authorized()

        return await handler(req, user)

    __wrapper.__name__ = handler.__name__
    return __wrapper
