import azure.functions as func
from http.cookies import SimpleCookie
from urllib.parse import unquote as url_unquote
import logging
from typing import Callable, Awaitable

from models import User
from apis.errors import not_authenticated, not_authorized, error_response
from services import tracer, STORAGE


def maybe_authenticated(handler: Callable[[func.HttpRequest, User | None], Awaitable[func.HttpResponse]]):
    """
    A decorator which is used to authenticate a user if they have provided an API key in the request.
    If the user is authenticated, the handler function is called with the request object and the authenticated
    user object. If the user is not authenticated, the handler is called with a None user object.

    :param handler:
        The handler function to call if the user is authenticated. This handler must be an async function
        and must accept two parameters: the incoming func.HttpRequest object and the authenticated model.User object.

    Example usage::

            @maybe_authenticated
            async def main(req: func.HttpRequest, user: User | None) -> func.HttpResponse:
                if user is None:
                    return func.HttpResponse("Hello, anonymous user!")
                return func.HttpResponse(f"Hello, {user.login}!")
    """

    async def _authenticate_internal(req: func.HttpRequest):
        with tracer.start_as_current_span("authenticate") as span:
            # Check the 'Authorization' header for the API key
            auth_token = get_auth_token(req)

            if not auth_token:
                logging.warning("No API key provided in the request.")
                return await handler(req, None)

            try:
                user = User.from_auth_token(auth_token)
            except Exception as ex:
                logging.warning("Error parsing auth token", exc_info=True)
                return await handler(req, None)

            stored_user = STORAGE.storage.get_user(user.login)
            if stored_user is None:
                return await handler(req, None)

            if stored_user.blocked:
                return await handler(req, None)
            if stored_user.api_key != user.api_key:
                return await handler(req, None)

            logging.debug("Authentication handler passed successfully.")
            return await handler(req, stored_user)

    _authenticate_internal.__name__ = handler.__name__
    return _authenticate_internal


def authenticated(handler: Callable[[func.HttpRequest, User], Awaitable[func.HttpResponse]]):
    """
    A decorator which is used to ensure that a user is authenticated before they can access a certain Azure
    Function HTTP handler. It supports both API key and Cookie based authentication schemes and will call
    the decorated handler function with both the request and the authenticated user object.

    :param handler:
        The handler function to call if the user is authenticated. This handler must be an async function
        and must accept two parameters: the incoming func.HttpRequest object and the authenticated model.User object.

    Example usage::

        @authenticated
        async def main(req: func.HttpRequest, user: User) -> func.HttpResponse:
            return func.HttpResponse(f"Hello, {user.login}!")

    """

    async def _authenticate_internal(req: func.HttpRequest, user: User | None):
        if user is None:
            return not_authenticated()

        return await handler(req, user)

    _authenticate_internal.__name__ = handler.__name__
    return maybe_authenticated(_authenticate_internal)


def get_auth_token(req: func.HttpRequest) -> str | None:
    api_key = req.headers.get("Authorization")
    if api_key is not None and api_key.startswith("Bearer "):
        return api_key.split("Bearer ")[1]

    cookies = SimpleCookie()
    cookies.load(req.headers.get("Cookie", ""))

    if "Auth" in cookies:
        return url_unquote(cookies["Auth"].value)

    return None
