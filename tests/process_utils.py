from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
WORK = ROOT / ".work"


def _venv_bin() -> Path:
    configured = os.environ.get("URIRUN_TEST_VENV")
    if configured:
        return Path(configured) / ("Scripts" if os.name == "nt" else "bin")
    return Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")


def transport_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = str(_venv_bin()) + os.pathsep + env.get("PATH", "")
    source_pythonpath = WORK / "source-pythonpath.txt"
    if source_pythonpath.exists():
        source = source_pythonpath.read_text(encoding="utf-8").strip()
        if source:
            env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if extra:
        env.update(extra)
    return env


def free_tcp_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_port(host: str, port: int, *, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"port did not open: {host}:{port}; last error: {last_error}")


def wait_for_port_or_process(host: str, port: int, managed: "ManagedProcess", *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        return_code = managed.process.poll()
        if return_code is not None:
            logs = managed.read_logs()
            raise RuntimeError(
                f"{managed.name} exited before opening {host}:{port}; "
                f"exit_code={return_code}; stdout={logs['stdout'][-4000:]}; stderr={logs['stderr'][-4000:]}"
            )
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.25)
    logs = managed.read_logs()
    raise TimeoutError(
        f"port did not open: {host}:{port}; last error: {last_error}; "
        f"stdout={logs['stdout'][-4000:]}; stderr={logs['stderr'][-4000:]}"
    )


@dataclass
class ManagedProcess:
    name: str
    command: list[str]
    process: subprocess.Popen[str]
    log_path: Path

    def terminate(self, timeout: float = 10.0) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)

    def read_logs(self) -> dict[str, str]:
        stdout_path = self.log_path.with_suffix(".stdout.log")
        stderr_path = self.log_path.with_suffix(".stderr.log")
        return {
            "stdout": stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else "",
            "stderr": stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else "",
        }


def start_process(name: str, command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> ManagedProcess:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    base = REPORT_DIR / name
    stdout = base.with_suffix(".stdout.log").open("w", encoding="utf-8", errors="replace")
    stderr = base.with_suffix(".stderr.log").open("w", encoding="utf-8", errors="replace")
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=cwd or ROOT,
        env=env or transport_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )
    stdout.close()
    stderr.close()
    return ManagedProcess(name=name, command=command, process=process, log_path=base)


def run_client(command: list[str], *, env: dict[str, str] | None = None, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env or transport_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def write_transport_report(
    name: str,
    *,
    transport: str,
    host: str,
    port: int | None,
    server_command: list[str] | None,
    client_command: list[str] | None,
    server_logs: dict[str, str] | None,
    client_result: subprocess.CompletedProcess[str] | None,
    urirun_version: str,
    recommendation: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "transport": transport,
        "host": host,
        "port": port,
        "server_command": server_command,
        "client_command": client_command,
        "server_stdout": (server_logs or {}).get("stdout", ""),
        "server_stderr": (server_logs or {}).get("stderr", ""),
        "client_stdout": "" if client_result is None else client_result.stdout,
        "client_stderr": "" if client_result is None else client_result.stderr,
        "exit_code": None if client_result is None else client_result.returncode,
        "os": platform.platform(),
        "python": sys.version,
        "urirun": urirun_version,
        "recommendation": recommendation,
        "extra": extra or {},
    }
    path = REPORT_DIR / f"{name}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
