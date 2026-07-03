from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"
VENV = WORK / "venv"
SRC = WORK / "urirun-src"
DEFAULT_REPO = "https://github.com/if-uri/urirun.git"
REPORT_DIR = ROOT / "reports"
INSTALL_META = WORK / "install-meta.json"
PUBLIC_RUNTIME_DEPS = [
    "jsonschema>=4.18",
    "pydantic>=2",
    "urirun-connector-router>=0.2.0",
    "urirun-flow>=0.2.2",
]


def bin_path(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return VENV / ("Scripts" if os.name == "nt" else "bin") / f"{name}{suffix}"


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd or ROOT, check=True)


def run_capture(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=cwd or ROOT, text=True, capture_output=True)


def write_install_warning(command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    path = REPORT_DIR / "install-warning.json"
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = [existing]
        except json.JSONDecodeError:
            existing = []
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "recommendation": (
            "Publish or vendor every dependency declared by adapters/python/pyproject.toml. "
            "The harness used a --no-deps fallback only to keep black-box CLI tests runnable."
        ),
    }
    existing.append(payload)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def sync_source() -> Path:
    local_source = os.environ.get("URIRUN_SOURCE_DIR")
    if local_source:
        source = Path(local_source).resolve()
        if not (source / "adapters" / "python" / "pyproject.toml").exists():
            raise SystemExit(f"URIRUN_SOURCE_DIR does not look like urirun: {source}")
        return source

    repo_url = os.environ.get("URIRUN_REPO_URL", DEFAULT_REPO)
    ref = os.environ.get("URIRUN_REF", "main")
    if SRC.exists():
        shutil.rmtree(SRC)
    clone = run_capture(["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(SRC)])
    if clone.returncode != 0:
        if SRC.exists():
            shutil.rmtree(SRC)
        run(["git", "clone", "--no-checkout", "--filter=blob:none", repo_url, str(SRC)])
        fetch = run_capture(["git", "fetch", "--depth", "1", "origin", ref], cwd=SRC)
        if fetch.returncode != 0:
            write_install_warning(["git", "fetch", "--depth", "1", "origin", ref], fetch)
        run(["git", "checkout", "--detach", ref], cwd=SRC)
    return SRC


def git_revision(source: Path) -> str:
    result = run_capture(["git", "rev-parse", "HEAD"], cwd=source)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def write_install_meta(source: Path, used_fallback: bool) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": str(source),
        "repo_url": os.environ.get("URIRUN_REPO_URL", DEFAULT_REPO),
        "ref": os.environ.get("URIRUN_REF", "main"),
        "revision": git_revision(source),
        "pythonpath": str(source / "adapters" / "python"),
        "used_install_fallback": used_fallback,
    }
    INSTALL_META.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    if not VENV.exists():
        run([sys.executable, str(ROOT / "scripts" / "bootstrap.py")])
    source = sync_source()
    (WORK / "source-pythonpath.txt").write_text(str(source / "adapters" / "python"), encoding="utf-8")
    python_pkg = source / "adapters" / "python"
    install_command = [str(bin_path("python")), "-m", "pip", "install", str(python_pkg)]
    result = run_capture(install_command)
    used_fallback = False
    if result.returncode != 0:
        used_fallback = True
        write_install_warning(install_command, result)
        for dep in PUBLIC_RUNTIME_DEPS:
            dep_command = [str(bin_path("python")), "-m", "pip", "install", dep]
            dep_result = run_capture(dep_command)
            if dep_result.returncode != 0:
                write_install_warning(dep_command, dep_result)
        run([str(bin_path("python")), "-m", "pip", "install", "--no-deps", str(python_pkg)])
    write_install_meta(source, used_fallback)
    run([str(bin_path("urirun")), "--version"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
