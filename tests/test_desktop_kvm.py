"""Desktop KVM E2E: drive a real virtual desktop through mesh kvm:// URIs.

A `docker/desktop-pc` container runs Xvfb + openbox + x11vnc + noVNC and a
real `urirun node serve --execute` with urirun-connector-kvm installed. The
harness (host role) registers the node in a mesh and automates a user task —
launch an app, type into it, verify, screenshot — exclusively through
`urirun host run` dispatches. noVNC (port 16080) is the live human view.

Gated: runs only with URIRUN_TEST_PROFILE=desktop-kvm-e2e or
URIRUN_DESKTOP_KVM_E2E=1 (needs Docker and a first image build).

Vendored wheels (docker/desktop-pc/vendor) must be refreshed when urirun or
its unpublished deps change:
    pip wheel --no-deps -w docker/desktop-pc/vendor \
        ../urirun-contract ../urirun-connector-router ../urirun-flow \
        ../urirun-connector-kvm .work/urirun-src/adapters/python
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests.conftest import REPORT_DIR, ROOT, run_cmd

COMPOSE_DIR = ROOT / "docker" / "desktop-pc"
NODE_PORT = int(os.environ.get("PC1_NODE_PORT", "18765"))
SCREENSHOT_DIR = REPORT_DIR / "screenshots" / "desktop-kvm"


def _profile_active() -> bool:
    if os.environ.get("URIRUN_DESKTOP_KVM_E2E", "") == "1":
        return True
    return os.environ.get("URIRUN_TEST_PROFILE", "") == "desktop-kvm-e2e"


pytestmark = pytest.mark.skipif(
    not _profile_active(),
    reason="desktop kvm tests run only in the desktop-kvm-e2e profile or with URIRUN_DESKTOP_KVM_E2E=1",
)


def _compose(*args: str, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return run_cmd(["docker", "compose", *args], cwd=COMPOSE_DIR, check=check, timeout=timeout)


@pytest.fixture(scope="module")
def desktop_mesh(tmp_path_factory):
    from tests.conftest import command_path

    cli = command_path("urirun")
    if shutil.which("docker") is None:
        pytest.skip("docker is not available on this runner")
    _compose("up", "-d", "--build", "--wait")
    mesh = tmp_path_factory.mktemp("mesh") / "mesh.json"
    init = run_cmd([cli, "host", "init", "--config", str(mesh)], check=False)
    if "mesh not available" in init.stdout + init.stderr:
        _compose("down", "-v", check=False)
        pytest.xfail(
            "urirun host mesh layer is unavailable on this install; "
            "see tests/test_mesh_host.py for the dependency-publishing xfail"
        )
    run_cmd(
        [cli, "host", "add-node", "pc1", f"http://127.0.0.1:{NODE_PORT}", "--kind", "pc", "--tag", "novnc",
         "--config", str(mesh)]
    )
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield mesh
    finally:
        _compose("down", "-v", check=False)


def _dispatch(cli, mesh: Path, uri: str, payload: dict) -> dict:
    cp = run_cmd(
        [cli, "host", "run", "pc1", uri, "--config", str(mesh), "--payload", json.dumps(payload)],
        timeout=120,
    )
    document = json.loads(cp.stdout)
    assert document.get("ok") is True, f"{uri} failed: {cp.stdout[:800]}"
    result = document.get("result", document)
    # isolated connector handlers run via function-subprocess and nest their
    # payload under result["value"]
    value = result.get("value") if isinstance(result, dict) else None
    return value if isinstance(value, dict) else result


def _save_screenshot(cli, mesh: Path, name: str) -> Path:
    result = _dispatch(cli, mesh, "kvm://host/screen/query/capture", {"base64": True})
    encoded = result.get("pngBase64", "")
    assert encoded, f"capture returned no inline image: {json.dumps(result)[:400]}"
    target = SCREENSHOT_DIR / f"{name}.png"
    target.write_bytes(base64.b64decode(encoded))
    assert target.stat().st_size > 1000
    return target


@pytest.mark.stable
def test_node_exposes_kvm_surface(cli, desktop_mesh):
    nodes = run_cmd([cli, "host", "nodes", "--config", str(desktop_mesh)])
    assert "pc1" in nodes.stdout and "up" in nodes.stdout
    report = _dispatch(cli, desktop_mesh, "kvm://host/doctor/query/report", {})
    (REPORT_DIR / "desktop-kvm-doctor.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    text = json.dumps(report)
    assert "capture" in text and "input" in text


@pytest.mark.stable
def test_user_journey_terminal_type_and_verify(cli, desktop_mesh):
    _save_screenshot(cli, desktop_mesh, "01-empty-desktop")

    _dispatch(
        cli, desktop_mesh, "app://host/desktop/command/launch",
        # large antialiased font so the tesseract OCR verify step reads reliably
        {"app": "xterm", "args": ["-fa", "DejaVu Sans Mono", "-fs", "18"], "settle": 2},
    )

    # the shell prompt overrides -T via escape codes, so accept any window on
    # the otherwise-empty desktop as the terminal we just launched
    deadline = time.time() + 30
    windows: list = []
    while time.time() < deadline:
        listing = _dispatch(cli, desktop_mesh, "kvm://host/window/query/list", {})
        windows = [w for w in listing.get("windows", []) if str(w).strip()]
        if windows:
            break
        time.sleep(1)
    assert windows, "no window appeared after launching xterm"

    _dispatch(cli, desktop_mesh, "kvm://host/window/command/focus", {"title": str(windows[0])})
    _dispatch(cli, desktop_mesh, "kvm://host/input/command/type", {"text": "echo URIRUN-KVM-E2E-READY"})
    _dispatch(cli, desktop_mesh, "kvm://host/input/command/key", {"key": "Return"})
    time.sleep(1)
    _save_screenshot(cli, desktop_mesh, "02-terminal-typed")

    verdict = _dispatch(cli, desktop_mesh, "kvm://host/ui/query/verify", {"expect": "URIRUN-KVM-E2E-READY"})
    assert verdict.get("present"), f"OCR verify missed the marker: {verdict}"
