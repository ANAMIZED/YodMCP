"""Serve the YodMCP WebMCP dashboard from web/."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def mount_webmcp(app: FastAPI) -> None:
    @app.get("/dashboard")
    def dashboard():
        return RedirectResponse(url="/web/dashboard.html", status_code=307)

    if WEB_DIR.is_dir():
        app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


def create_api_app_with_web():
    from yodmcp.api.app import create_api_app

    app = create_api_app()
    mount_webmcp(app)
    return app


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="YodMCP Server OS API + WebMCP dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(create_api_app_with_web(), host=args.host, port=args.port)
