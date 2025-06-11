from typing import Callable, Awaitable
import logging

import azure.functions as func

from apis.errors import internal_error


def error_handler(handler: Callable[[func.HttpRequest], Awaitable[func.HttpResponse]]):
    """
    Decorates an Azure Function HTTP handler to catch exceptions and return an API error response.

    :param handler:
        The handler function to call if the user is authenticated. This handler must be an async function
        and must accept two parameters: the incoming func.HttpRequest object and the authenticated model.User object.

    Example usage::

        @error_handler
        async def main(req: func.HttpRequest) -> func.HttpResponse:
            return func.HttpResponse(f"Hello, World!")
    """

    async def _error_handler(req: func.HttpRequest) -> func.HttpResponse:
        try:
            return await handler(req)
        except Exception as ex:
            logging.error("Error processing request", exc_info=True)
            return internal_error()

    _error_handler.__name__ = handler.__name__

    return _error_handler
