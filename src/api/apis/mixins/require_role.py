import azure.functions as func
from typing import Callable, Awaitable

from models import User
from apis.errors import not_authorized


def require_role(*roles: str):
    """
    Ensures that the authenticated user has one of the specified roles before allowing them to access the
    decorated handler function. If the user does not have one of the specified roles, it will return a 403
    Forbidden error.

    This method is intended to be used in conjunction with the @authenticated decorator, and must always be
    applied after the @authenticated decorator in the handler chain.

    :param roles:
        A list of roles that the user must have in order to access the decorated handler function.

    Example usage::

        @authenticated
        @require_role("admin")
        async def main(req: func.HttpRequest, user: User) -> func.HttpResponse:
            return func.HttpResponse(f"Hello, {user.login}! You are a {user.role}.")
    """

    def __decorator(handler: Callable[[func.HttpRequest, User], Awaitable[func.HttpResponse]]):
        async def __wrapper(req: func.HttpRequest, user: User):
            if user.role not in roles:
                return not_authorized()
            return await handler(req, user)

        __wrapper.__name__ = handler.__name__
        return __wrapper

    return __decorator
