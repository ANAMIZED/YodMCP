"""CLI entry for YodMCP."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from yodmcp.core.server import create_server
from yodmcp.core.substrate import init_substrate


def main() -> None:
    parser = argparse.ArgumentParser(description="YodMCP — Ultimate Autonomous MCP Server")
    parser.add_argument("--http", action="store_true", help="Streamable HTTP transport")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--trace", action="store_true", help="Console OpenTelemetry spans")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    init_substrate(console_tracing=args.trace)
    server = create_server()

    if args.http:
        print(f"YodMCP HTTP on http://{args.host}:{args.port}/mcp", file=sys.stderr)
        asyncio.run(server.run_streamable_http_async(host=args.host, port=args.port))
    else:
        print("YodMCP stdio transport", file=sys.stderr)
        asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
