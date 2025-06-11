import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.trace import SpanKind, StatusCode, Status, Link
from opentelemetry.sdk.resources import Resource


def span_formatter(span) -> str:
    return f"{span.name} ({str(span.kind)}) {repr(span.attributes)}\n"


# Configure OpenTelemetry to use Azure Monitor with the
# APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.
# See: https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") is not None:
    configure_azure_monitor(resource=Resource.create({"service.name": "llmail-api"}))
else:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(formatter=span_formatter)))
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("api")
