from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import paramiko

from .config import AppConfig

GPU_QUERY_FIELDS = [
    "index",
    "name",
    "temperature.gpu",
    "utilization.gpu",
    "memory.total",
    "memory.used",
    "power.draw",
    "power.limit",
    "fan.speed",
]


def _parse_csv_rows(text: str) -> List[List[str]]:
    rows: List[List[str]] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row:
            continue
        rows.append([cell.strip() for cell in row])
    return rows


def _safe_float(value: str) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    if value in {"N/A", "Not Supported"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _safe_int(value: str) -> Optional[int]:
    number = _safe_float(value)
    if number is None:
        return None
    return int(round(number))


def _normalize_gpu_row(fields: List[str], row: List[str]) -> Dict[str, Optional[float]]:
    raw = dict(zip(fields, row))
    memory_total = _safe_float(raw.get("memory.total", ""))
    memory_used = _safe_float(raw.get("memory.used", ""))

    memory_util = None
    if memory_total and memory_total > 0 and memory_used is not None:
        memory_util = round((memory_used / memory_total) * 100, 1)

    return {
        "index": _safe_int(raw.get("index", "")),
        "name": raw.get("name") or "Unknown",
        "temperature_c": _safe_float(raw.get("temperature.gpu", "")),
        "utilization_gpu": _safe_float(raw.get("utilization.gpu", "")),
        "memory_total_mb": memory_total,
        "memory_used_mb": memory_used,
        "memory_utilization": memory_util,
        "power_draw_w": _safe_float(raw.get("power.draw", "")),
        "power_limit_w": _safe_float(raw.get("power.limit", "")),
        "fan_speed_pct": _safe_float(raw.get("fan.speed", "")),
    }


def _summarize_gpus(gpus: List[Dict[str, Optional[float]]]) -> Dict[str, Optional[float]]:
    def _avg(values: List[Optional[float]]) -> Optional[float]:
        filtered = [v for v in values if v is not None]
        if not filtered:
            return None
        return round(sum(filtered) / len(filtered), 2)

    memory_used = sum(gpu["memory_used_mb"] or 0 for gpu in gpus)
    memory_total = sum(gpu["memory_total_mb"] or 0 for gpu in gpus)
    memory_util = None
    if memory_total > 0:
        memory_util = round((memory_used / memory_total) * 100, 1)

    return {
        "gpu_count": len(gpus),
        "memory_used_mb": round(memory_used, 1),
        "memory_total_mb": round(memory_total, 1),
        "memory_utilization": memory_util,
        "utilization_avg": _avg([gpu["utilization_gpu"] for gpu in gpus]),
        "temperature_avg": _avg([gpu["temperature_c"] for gpu in gpus]),
        "power_draw_avg": _avg([gpu["power_draw_w"] for gpu in gpus]),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class GpuPoller:
    def __init__(self, config: AppConfig, update_callback: Callable[[Optional[dict], Optional[str]], None]):
        self._config = config
        self._update_callback = update_callback
        self._stop = False
        self._client: Optional[paramiko.SSHClient] = None

    def stop(self) -> None:
        self._stop = True
        self._disconnect()

    def run(self) -> None:
        while not self._stop:
            start = time.time()
            data, error = self._collect()
            self._update_callback(data, error)
            elapsed = time.time() - start
            sleep_for = max(self._config.poll_interval - elapsed, 0.1)
            time.sleep(sleep_for)

    def _collect(self) -> Tuple[Optional[dict], Optional[str]]:
        missing = []
        if not self._config.server_host:
            missing.append("server_host")
        if not self._config.server_user:
            missing.append("server_user")
        if not (self._config.server_password or self._config.server_key_path):
            missing.append("server_password_or_key")
        if self._config.server_key_path:
            key_path = Path(self._config.server_key_path)
            if not key_path.exists():
                return None, f"SSH key not found: {key_path}"
        if missing:
            return None, f"Missing config: {', '.join(missing)}"

        try:
            if not self._is_connected():
                self._connect()
            command = (
                "LC_ALL=C nvidia-smi --query-gpu="
                + ",".join(GPU_QUERY_FIELDS)
                + " --format=csv,noheader,nounits"
            )
            output = self._exec(command)
            rows = _parse_csv_rows(output)
            gpus = [_normalize_gpu_row(GPU_QUERY_FIELDS, row) for row in rows]
            summary = _summarize_gpus(gpus)
            driver_version = self._fetch_driver_version()
            data = {
                "timestamp": _now_iso(),
                "gpus": gpus,
                "summary": summary,
                "driver_version": driver_version,
            }
            return data, None
        except Exception as exc:  # pylint: disable=broad-except
            self._disconnect()
            return None, str(exc)

    def _connect(self) -> None:
        client = paramiko.SSHClient()
        if self._config.allow_unknown_hosts:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            client.load_system_host_keys()
        client.connect(
            hostname=self._config.server_host,
            port=self._config.server_port,
            username=self._config.server_user,
            password=self._config.server_password,
            key_filename=self._config.server_key_path,
            timeout=self._config.ssh_connect_timeout,
            banner_timeout=self._config.ssh_connect_timeout,
            auth_timeout=self._config.ssh_connect_timeout,
        )
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(10)
        self._client = client

    def _disconnect(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        finally:
            self._client = None

    def _is_connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def _exec(self, command: str) -> str:
        if self._client is None:
            raise RuntimeError("SSH client not connected")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=self._config.ssh_command_timeout)
        stdin.close()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            message = error.strip() or f"Command failed with exit code {exit_status}"
            raise RuntimeError(message)
        return output

    def _fetch_driver_version(self) -> Optional[str]:
        try:
            output = self._exec("LC_ALL=C nvidia-smi --query-gpu=driver_version --format=csv,noheader")
            rows = _parse_csv_rows(output)
            if rows and rows[0]:
                return rows[0][0]
        except Exception:
            return None
        return None
