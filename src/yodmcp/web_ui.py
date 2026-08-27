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
