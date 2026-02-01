from __future__ import annotations

import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import AppConfig, load_config
from .poller import GpuPoller


def _resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    base = Path(__file__).resolve().parent
    return base / relative


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AppState:
    def __init__(self, config: AppConfig) -> None:
        self._lock = threading.Lock()
        self._data: Optional[dict] = None
        self._error: Optional[str] = None
        self._last_update: Optional[str] = None
        self._config = config
        self._config_errors = self._validate_config()

    def _validate_config(self) -> list[str]:
        errors = []
        if not self._config.server_host:
            errors.append("server_host")
        if not self._config.server_user:
            errors.append("server_user")
        if not (self._config.server_password or self._config.server_key_path):
            errors.append("server_password_or_key")
        return errors

    def update(self, data: Optional[dict], error: Optional[str]) -> None:
        with self._lock:
            self._data = data
            self._error = error
            self._last_update = _now_iso()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "ok": self._error is None and self._data is not None,
                "error": self._error,
                "last_update": self._last_update,
                "config_errors": self._config_errors,
                "data": self._data,
                "server": {
                    "host": self._config.server_host,
                    "port": self._config.server_port,
                    "user": self._config.server_user,
                },
                "poll_interval": self._config.poll_interval,
            }


config = load_config()
state = AppState(config)
app = FastAPI()
static_dir = _resource_path("static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

_poll_thread: Optional[threading.Thread] = None
_poller: Optional[GpuPoller] = None


@app.on_event("startup")
def _on_startup() -> None:
    global _poll_thread
    global _poller

    def _update(data: Optional[dict], error: Optional[str]) -> None:
        state.update(data, error)

    _poller = GpuPoller(config, _update)
    _poll_thread = threading.Thread(target=_poller.run, daemon=True)
    _poll_thread.start()


@app.on_event("shutdown")
def _on_shutdown() -> None:
    if _poller is not None:
        _poller.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(state.snapshot())


@app.get("/api/health")
def api_health() -> JSONResponse:
    return JSONResponse({"ok": True, "timestamp": _now_iso()})


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        return


if __name__ == "__main__":
    url = f"http://{config.local_host}:{config.local_port}"
    threading.Timer(1.0, _open_browser, args=(url,)).start()
    uvicorn.run(app, host=config.local_host, port=config.local_port, log_level="info")
