from typing import Callable, Awaitable
import azure.functions as func

from services.telemetry import tracer, SpanKind, StatusCode


def instrumented(route: str):
    """
    Decorates an Azure Function HTTP handler to create a new trace span for each incoming request,
    automatically populating appropriate attributes and setting the span status based on the response.

    The span is automatically closed when the handler returns or throws an exception.

    :param str route:
        The route of the API endpoint, e.g. `/teams/{team_id}/jobs`.

    Example usage::

        @instrumented("/teams")
        async def main(req: func.HttpRequest) -> func.HttpResponse:
            return func.HttpResponse("Hello, World!")
    """

    def decorator(handler: Callable[[func.HttpRequest], Awaitable[func.HttpResponse]]):
        async def _instrumented_api(req: func.HttpRequest) -> func.HttpResponse:
            with tracer.start_as_current_span(
                f"{req.method} {route}",
                kind=SpanKind.SERVER,
                attributes={
                    "http.method": req.method,
                    "http.route": route,
                    "http.url": req.url,
                    "http.user_agent": req.headers.get("User-Agent"),
                    "http.host": req.headers.get("Host"),
                },
            ) as span:
                resp = await handler(req)

                if isinstance(resp, func.HttpResponse):
                    span.set_attribute("http.status_code", resp.status_code)

                    if resp.status_code >= 400:
                        text = (
                            resp.get_body().decode("utf-8") if resp.get_body() else f"HTTP {resp.status_code}"
                        )
                        span.set_status(StatusCode.ERROR, text)

                return resp

        _instrumented_api.__name__ = handler.__name__
        return _instrumented_api

    return decorator
