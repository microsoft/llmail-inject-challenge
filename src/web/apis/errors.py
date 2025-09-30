import azure.functions as func
import json

from services.telemetry import trace


def error_response(code: int, message: str, advice: str) -> func.HttpResponse:
    """
    Constructs a standard error response for an API endpoint.
    """

    return func.HttpResponse(
        json.dumps(
            {
                "message": message,
                "advice": advice,
                "trace_id": trace.format_trace_id(trace.get_current_span().get_span_context().trace_id),
            }
        ),
        status_code=code,
        mimetype="application/json",
    )


def not_authenticated() -> func.HttpResponse:
    return error_response(
        401,
        "You have not provided a valid API key in the Authorization header.",
        "Please provide your API key in the Authorization header as 'Bearer <your api key>' and try again.",
    )


def not_authorized() -> func.HttpResponse:
    return error_response(
        403,
        "You are not authorized to access this resource.",
        "Please make sure that you have the appropriate permissions and try again. You may need to contact a member of the team to be added.",
    )


def internal_error() -> func.HttpResponse:
    return error_response(
        500,
        "An unexpected error occurred while processing your request.",
        "If you repeatedly experience this issue, please report it to the competition organizers along with the included trace ID.",
    )
