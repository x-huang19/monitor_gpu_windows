from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    server_host: Optional[str]
    server_user: Optional[str]
    server_password: Optional[str]
    server_key_path: Optional[str]
    server_port: int
    poll_interval: float
    local_host: str
    local_port: int
    ssh_connect_timeout: int
    ssh_command_timeout: int
    allow_unknown_hosts: bool
    config_path: Path


def _default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "config.json"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _env_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    return None


def _env_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _env_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _expand_path(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(Path(value).expanduser())


def load_config() -> AppConfig:
    config_path = Path(os.getenv("GPU_MONITOR_CONFIG", _default_config_path()))
    data = _load_json(config_path)

    server_host = os.getenv("GPU_SERVER_HOST", data.get("server_host"))
    server_user = os.getenv("GPU_SERVER_USER", data.get("server_user"))
    server_password = os.getenv("GPU_SERVER_PASSWORD", data.get("server_password"))
    server_key_path = os.getenv("GPU_SERVER_KEY_PATH", data.get("server_key_path"))

    server_port = _env_int(os.getenv("GPU_SERVER_PORT")) or int(data.get("server_port", 22))
    poll_interval = _env_float(os.getenv("GPU_POLL_INTERVAL")) or float(data.get("poll_interval", 1.0))
    local_host = os.getenv("GPU_LOCAL_HOST", data.get("local_host", "127.0.0.1"))
    local_port = _env_int(os.getenv("GPU_LOCAL_PORT")) or int(data.get("local_port", 8787))

    ssh_connect_timeout = _env_int(os.getenv("GPU_SSH_CONNECT_TIMEOUT")) or int(
        data.get("ssh_connect_timeout", 5)
    )
    ssh_command_timeout = _env_int(os.getenv("GPU_SSH_COMMAND_TIMEOUT")) or int(
        data.get("ssh_command_timeout", 5)
    )

    allow_unknown_hosts = _env_bool(os.getenv("GPU_SSH_ALLOW_UNKNOWN_HOSTS"))
    if allow_unknown_hosts is None:
        allow_unknown_hosts = bool(data.get("allow_unknown_hosts", True))

    return AppConfig(
        server_host=server_host or None,
        server_user=server_user or None,
        server_password=server_password or None,
        server_key_path=_expand_path(server_key_path),
        server_port=server_port,
        poll_interval=max(poll_interval, 0.5),
        local_host=local_host,
        local_port=local_port,
        ssh_connect_timeout=ssh_connect_timeout,
        ssh_command_timeout=ssh_command_timeout,
        allow_unknown_hosts=allow_unknown_hosts,
        config_path=config_path,
    )
