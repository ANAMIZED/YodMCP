"""CLI entry for YodMCP."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from yodmcp.core.server import create_server
from yodmcp.core.substrate import init_substrate
from yodmcp.observability.logging import configure_logging
from yodmcp.security.auth import auth_required, check_api_key_headers


def main() -> None:
    parser = argparse.ArgumentParser(description="YodMCP — Ultimate Autonomous MCP Server")
    parser.add_argument("--http", action="store_true", help="Streamable HTTP transport")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--trace", action="store_true", help="Console OpenTelemetry spans")
    args = parser.parse_args()

    configure_logging(args.log_level)
    init_substrate(console_tracing=args.trace)
    server = create_server()

    if args.http:
        print(f"YodMCP HTTP on http://{args.host}:{args.port}/mcp", file=sys.stderr)
        if auth_required():
            print("Auth required on MCP HTTP (YODMCP_API_KEY set)", file=sys.stderr)

        # Wrap Streamable HTTP ASGI app with API-key middleware when keys configured
        import uvicorn
        from starlette.applications import Starlette
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse

        base_app = server.streamable_http_app()

        class McpAuthMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                path = request.url.path
                # Allow health-style probes if any
                if path.rstrip("/").endswith("/health"):
                    return await call_next(request)
                if auth_required():
                    headers = {k.decode() if isinstance(k, bytes) else k: (
                        v.decode() if isinstance(v, bytes) else v
                    ) for k, v in request.headers.items()}
                    # starlette headers are already str
                    headers = dict(request.headers)
                    if not check_api_key_headers(headers):
                        return JSONResponse(
                            {"error": "Unauthorized — provide Authorization Bearer or X-API-Key"},
                            status_code=401,
                        )
                    from yodmcp.core.tenant import set_tenant
                    tenant = request.headers.get("x-yodmcp-tenant") or "default"
                    set_tenant(tenant)
                return await call_next(request)

        app = Starlette()
        # Mount by wrapping: use middleware on a host that delegates
        # Simplest: re-use base_app and add middleware to it
        base_app.add_middleware(McpAuthMiddleware)
        uvicorn.run(base_app, host=args.host, port=args.port)
    else:
        print("YodMCP stdio transport", file=sys.stderr)
        asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
