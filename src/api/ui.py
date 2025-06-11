import azure.functions as func
import os
import requests

from apis.errors import error_response

ui = func.Blueprint()

UI_PROXY_URL = os.getenv("UI_PROXY_URL")

UI_FILE_CACHE: dict[str, func.HttpResponse] = {}


@ui.route("{*path}", methods=["GET"])
def ui_proxy(req: func.HttpRequest) -> func.HttpResponse:
    path = req.route_params.get("path", "")
    if path.startswith("api/"):
        return error_response(
            405,
            "This API is not implemented by the server.",
            "Please make sure that you are using a valid API endpoint, consult the API documentation and try again.",
        )

    if UI_PROXY_URL is None:
        return func.HttpResponse(
            status_code=404,
            body="UI is not configured",
            mimetype="text/plain",
        )

    if path in UI_FILE_CACHE:
        return UI_FILE_CACHE[path]

    resp = requests.get(f"{UI_PROXY_URL}/{path}")
    content_type = resp.headers.get("content-type", "application/octet-stream")

    UI_FILE_CACHE[path] = func.HttpResponse(
        status_code=resp.status_code,
        body=resp.content,
        mimetype=content_type,
    )

    return UI_FILE_CACHE[path]
