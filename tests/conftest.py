from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
REGISTRY = ROOT / "fixtures" / "registry.json"
WORK = ROOT / ".work"
MESH_UNAVAILABLE_XFAIL = (
    "urirun host/node mesh layer is unavailable after a fresh install: "
    "urirun-contract / urirun-connector-router / urirun-flow>=0.2.2 are not "
    "published, so the harness --no-deps fallback leaves urirun_flow missing."
)


def _venv_bin() -> Path:
    configured = os.environ.get("URIRUN_TEST_VENV")
    if configured:
        return Path(configured) / ("Scripts" if os.name == "nt" else "bin")
    return Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")


def _command_path(name: str) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    candidate = _venv_bin() / f"{name}{suffix}"
    return str(candidate) if candidate.exists() else name


def command_path(name: str) -> str:
    return _command_path(name)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    bin_dir = str(_venv_bin())
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    source_pythonpath = WORK / "source-pythonpath.txt"
    if source_pythonpath.exists():
        extra = source_pythonpath.read_text(encoding="utf-8").strip()
        if extra:
            env["PYTHONPATH"] = extra + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("URIRUN_ERRORS", "1")
    env.setdefault("URIRUN_ERROR_LOG", str(REPORT_DIR / "urirun-errors.jsonl"))
    return env


def write_failure_report(
    name: str,
    command: list[str],
    result: subprocess.CompletedProcess[str] | None,
    exc: BaseException | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "test": name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "system": {
            "os": platform.platform(),
            "python": sys.version,
            "node": node_version(),
        },
        "urirun": urirun_version(best_effort=True),
        "command": command,
        "exit_code": None if result is None else result.returncode,
        "stdout": "" if result is None else result.stdout,
        "stderr": "" if result is None else result.stderr,
        "stack_trace": None if exc is None else "".join(traceback.format_exception(exc)),
        "recommendation": recommendation(result, exc),
    }
    path = REPORT_DIR / f"{name}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def recommendation(result: subprocess.CompletedProcess[str] | None, exc: BaseException | None) -> str:
    text = ((result.stdout if result else "") + "\n" + (result.stderr if result else "")).lower()
    if exc is not None:
        return "Inspect the Python stack trace and verify the test environment paths."
    if "no allow rule" in text or "permission" in text or "policy" in text:
        return "Check --allow policy globs and avoid broadening them beyond the tested URI scheme."
    if "mesh not available" in text:
        return "Install or publish the urirun mesh dependencies required by host/node commands, then rerun the E2E harness."
    if "no such file" in text or "not found" in text:
        return "Verify the registry path, command availability, and PATH inside the test virtualenv."
    if "schema" in text or "invalid" in text:
        return "Compare the payload with the route inputSchema in fixtures/registry.json."
    return "Re-run the failing command locally with the same environment and inspect stdout/stderr."


def node_version() -> str | None:
    try:
        cp = subprocess.run(["node", "--version"], text=True, capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return cp.stdout.strip() or cp.stderr.strip() or None


def urirun_version(best_effort: bool = False) -> str:
    try:
        cp = run_cmd([_command_path("urirun"), "--version"], check=not best_effort, timeout=30)
    except Exception:
        if best_effort:
            return "unavailable"
        raise
    return (cp.stdout or cp.stderr).strip()


def run_cmd(
    command: list[str],
    *,
    check: bool = True,
    timeout: int = 60,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        command,
        cwd=cwd or ROOT,
        env=_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    if check and cp.returncode != 0:
        write_failure_report("command_failure", command, cp)
        raise AssertionError(f"command failed with {cp.returncode}: {' '.join(command)}\n{cp.stderr}")
    return cp


def xfail_if_mesh_unavailable(output: str) -> None:
    if "mesh not available" in output:
        pytest.xfail(MESH_UNAVAILABLE_XFAIL)


def run_shell(command: str, *, shell_name: str, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    if shell_name == "bash":
        executable = shutil.which("bash")
        if not executable:
            pytest.skip("bash is not available on this runner")
        argv = [executable, "-lc", command]
    elif shell_name == "powershell":
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if not executable:
            pytest.skip("PowerShell is not available on this runner")
        argv = [executable, "-NoProfile", "-Command", command]
    elif shell_name == "cmd":
        if os.name != "nt":
            pytest.skip("cmd.exe is Windows-only")
        argv = ["cmd.exe", "/d", "/c", command]
    else:
        raise ValueError(f"unsupported shell: {shell_name}")
    return run_cmd(argv, check=check, timeout=timeout)


@pytest.fixture
def cli() -> str:
    return _command_path("urirun")


@pytest.fixture
def registry_path() -> str:
    return str(REGISTRY)


@pytest.fixture
def python_executable() -> str:
    return _command_path("python")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        write_failure_report(item.name, ["pytest", item.nodeid], None, call.excinfo.value if call.excinfo else None)
