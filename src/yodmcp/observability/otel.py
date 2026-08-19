"""OpenTelemetry trajectory instrumentation for YodMCP."""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor, BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode, Span

from yodmcp import __version__

_provider: TracerProvider | None = None


def init_tracing(service_name: str = "yodmcp", console: bool = True) -> TracerProvider:
    global _provider
    if _provider is not None:
        return _provider
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": __version__,
            "deployment.environment": os.environ.get("YODMCP_ENV", "dev"),
        }
    )
    provider = TracerProvider(resource=resource)

    # Console exporter (dev)
    if console or os.environ.get("YODMCP_OTEL_CONSOLE", "").lower() in ("1", "true", "yes"):
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # OTLP exporter when endpoint configured (prod)
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get(
        "YODMCP_OTLP_ENDPOINT"
    )
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            # Optional dep; fall back silently if not installed
            pass

    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def get_tracer(name: str = "yodmcp") -> trace.Tracer:
    if _provider is None:
        init_tracing()
    return trace.get_tracer(name)


def start_tool_span(tool_name: str, attributes: dict[str, Any] | None = None) -> Span:
    tracer = get_tracer()
    span = tracer.start_span(f"tool.{tool_name}")
    span.set_attribute("mcp.tool.name", tool_name)
    if attributes:
        for k, v in attributes.items():
            if v is not None:
                span.set_attribute(k, str(v)[:256])
    return span


def end_span(span: Span, ok: bool = True, error: str | None = None) -> None:
    if not ok:
        span.set_status(Status(StatusCode.ERROR, error or "error"))
        if error:
            span.record_exception(Exception(error))
    else:
        span.set_status(Status(StatusCode.OK))
    span.end()
