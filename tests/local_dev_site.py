from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.process_utils import ManagedProcess, free_tcp_port, start_process


@dataclass(frozen=True)
class DevServerPlan:
    status: str
    stack: str
    command: list[str] | None
    cwd: str
    port: int | None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stack": self.stack,
            "command": self.command,
            "cwd": self.cwd,
            "port": self.port,
            "reason": self.reason,
        }


def _package_manager(checkout: Path) -> str:
    if (checkout / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (checkout / "yarn.lock").exists():
        return "yarn"
    return "npm"


def detect_dev_server(checkout: Path, *, host: str = "127.0.0.1") -> DevServerPlan:
    port = free_tcp_port(host)
    package_json = checkout / "package.json"
    if package_json.exists():
        package = json.loads(package_json.read_text(encoding="utf-8"))
        scripts = package.get("scripts", {})
        manager = _package_manager(checkout)
        for script in ("dev", "start"):
            if script in scripts:
                command = [manager, "run", script, "--", "--host", host, "--port", str(port)]
                return DevServerPlan("detected", f"node-{manager}", command, str(checkout), port)
        if "build" in scripts:
            return DevServerPlan("integration_required", f"node-{manager}", None, str(checkout), None, "package.json has build but no stable dev/start script")
        return DevServerPlan("integration_required", f"node-{manager}", None, str(checkout), None, "package.json has no dev/start/build script")
    if (checkout / "index.html").exists():
        command = [sys.executable, "-m", "http.server", str(port), "--bind", host]
        return DevServerPlan("detected", "static-html", command, str(checkout), port)
    public = checkout / "public"
    if (public / "index.html").exists():
        command = [sys.executable, "-m", "http.server", str(port), "--bind", host]
        return DevServerPlan("detected", "static-html-public", command, str(public), port)
    return DevServerPlan("integration_required", "unknown", None, str(checkout), None, "no package.json or static index.html was found")


def copy_bundle_into_checkout(bundle_dir: Path, checkout: Path) -> list[str]:
    copied: list[str] = []
    target = checkout / "deployment-bundle"
    if target.exists():
        shutil.rmtree(target)
    if bundle_dir.exists():
        shutil.copytree(bundle_dir, target)
        copied.append(str(target))
    artifacts_source = bundle_dir / "artifacts"
    artifacts_target = checkout / "artifacts"
    artifacts_target.mkdir(parents=True, exist_ok=True)
    if artifacts_source.exists():
        for artifact in artifacts_source.iterdir():
            if artifact.is_file():
                shutil.copy2(artifact, artifacts_target / artifact.name)
                copied.append(str(artifacts_target / artifact.name))
    return copied


def clone_checkout(repo: str, ref: str, checkout: Path, *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    if checkout.exists():
        shutil.rmtree(checkout)
    return subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, repo, str(checkout)],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def start_detected_server(plan: DevServerPlan) -> tuple[ManagedProcess, str]:
    if not plan.command or not plan.port:
        raise ValueError(f"dev server command is not available: {plan.reason}")
    process = start_process("local-dev-site", plan.command, cwd=Path(plan.cwd))
    return process, f"http://127.0.0.1:{plan.port}/"
