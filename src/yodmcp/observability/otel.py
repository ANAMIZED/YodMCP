"""OpenTelemetry trajectory instrumentation for YodMCP."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode, Span

_provider: TracerProvider | None = None


def init_tracing(service_name: str = "yodmcp", console: bool = True) -> TracerProvider:
    global _provider
    if _provider is not None:
        return _provider
    resource = Resource.create({"service.name": service_name, "service.version": "0.1.0"})
    provider = TracerProvider(resource=resource)
    if console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
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
