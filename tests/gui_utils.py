from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import command_path, node_version, urirun_version
from tests.process_utils import ManagedProcess, free_tcp_port, start_process, transport_env


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
SCREENSHOT_DIR = REPORT_DIR / "screenshots"
TRACE_DIR = REPORT_DIR / "traces"
INSTALLER_DIR = REPORT_DIR / "installer"


def ensure_report_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        pytest.skip(f"Playwright is not installed or browsers are unavailable: {exc}")
    return sync_playwright


def current_system() -> dict[str, str | None]:
    return {
        "os": platform.platform(),
        "python": sys.version,
        "node": node_version(),
        "urirun": urirun_version(best_effort=True),
    }


def write_json_report(name: str, payload: dict[str, Any]) -> Path:
    ensure_report_dirs()
    path = REPORT_DIR / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _patterns_from_env(name: str) -> list[re.Pattern[str]]:
    raw = os.environ.get(name, "")
    patterns = [part.strip() for part in raw.splitlines() if part.strip()]
    if not patterns and raw.strip():
        patterns = [part.strip() for part in raw.split(";") if part.strip()]
    return [re.compile(pattern) for pattern in patterns]


def is_allowed_message(message: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(message) for pattern in patterns)


def split_allowed_messages(messages: list[str], patterns: list[re.Pattern[str]]) -> tuple[list[str], list[str]]:
    accepted: list[str] = []
    critical: list[str] = []
    for message in messages:
        if is_allowed_message(message, patterns):
            accepted.append(message)
        else:
            critical.append(message)
    return accepted, critical


def classify_browser_events(events: dict[str, list[str]]) -> dict[str, list[str]]:
    accepted_console, critical_console = split_allowed_messages(
        events.get("console_errors", []),
        _patterns_from_env("URIRUN_GUI_ALLOWED_CONSOLE_ERROR_PATTERNS"),
    )
    accepted_requests, critical_requests = split_allowed_messages(
        events.get("failed_requests", []),
        _patterns_from_env("URIRUN_GUI_ALLOWED_NETWORK_ERROR_PATTERNS"),
    )
    return {
        "accepted_console_errors": accepted_console,
        "critical_console_errors": critical_console,
        "accepted_failed_requests": accepted_requests,
        "critical_failed_requests": critical_requests,
    }


def retention_mode(name: str, default: str) -> str:
    mode = os.environ.get(name, default).strip().lower()
    if mode not in {"always", "on-failure", "off"}:
        raise ValueError(f"{name} must be always, on-failure, or off; got {mode!r}")
    return mode


def should_keep_artifact(mode: str, *, failed: bool) -> bool:
    return mode == "always" or (mode == "on-failure" and failed)


def selector_candidates(name: str) -> list[str]:
    slug = name.lower().replace(" ", "-")
    return [
        f'[data-testid="{slug}"]',
        f'[aria-label="{name}"]',
        f'role=button[name=/{re.escape(name)}/i]',
        f'text=/{re.escape(name)}/i',
    ]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_text(url: str, *, timeout: float = 30.0) -> tuple[int | None, str, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "urirun-multiplatform-test"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return int(getattr(response, "status", 200)), body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)


def monitor_page(page) -> dict[str, list[str]]:
    events: dict[str, list[str]] = {"console_errors": [], "failed_requests": []}

    def on_console(message) -> None:
        if message.type == "error":
            events["console_errors"].append(f"{message.type}: {message.text}")

    def on_request_failed(request) -> None:
        failure = request.failure
        error_text = failure.get("errorText") if isinstance(failure, dict) else str(failure)
        events["failed_requests"].append(f"{request.method} {request.url} {error_text}")

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)
    return events


def wait_http_ready(url: str, *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= int(getattr(response, "status", 200)) < 500:
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"HTTP endpoint did not become ready: {url}; last error: {last_error}")


def isolated_home(name: str) -> Path:
    path = ROOT / ".work" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def isolated_env(home: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = transport_env(extra)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["URIRUN_HOME"] = str(home / ".urirun")
    env["PATH"] = os.pathsep.join([
        str(home / ".local" / "bin"),
        str(home / "bin"),
        str(home / ".urirun" / "bin"),
        env.get("PATH", ""),
    ])
    return env


def start_dashboard(project: Path, *, host: str = "127.0.0.1") -> tuple[ManagedProcess, str]:
    ensure_report_dirs()
    port = free_tcp_port(host)
    db = project / "host.db"
    command = [
        command_path("urirun"),
        "host",
        "dashboard",
        "serve",
        "--project",
        str(project),
        "--db",
        str(db),
        "--host",
        host,
        "--port",
        str(port),
    ]
    process = start_process("gui-dashboard", command, env=isolated_env(isolated_home("gui-home")), cwd=ROOT)
    url = f"http://{host}:{port}/"
    wait_http_ready(f"{url}api/health", timeout=60)
    return process, url


def run_capture(command: list[str], *, env: dict[str, str] | None = None, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
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


def find_executable(name: str, env: dict[str, str]) -> str | None:
    suffix = ".exe" if os.name == "nt" else ""
    for folder in env.get("PATH", "").split(os.pathsep):
        candidate = Path(folder) / f"{name}{suffix}"
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name, path=env.get("PATH"))
    return found
