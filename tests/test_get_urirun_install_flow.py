from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

import pytest

from tests.gui_utils import (
    INSTALLER_DIR,
    current_system,
    fetch_text,
    find_executable,
    isolated_env,
    isolated_home,
    run_capture,
    sha256_file,
    write_json_report,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("URIRUN_USER_JOURNEY_ACTIVE") != "1",
    reason="user journey tests run only in installer-gui-e2e/user-journey profile or when explicitly targeted through scripts/run_tests.py",
)


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"


def _load_install_meta() -> dict:
    path = WORK / "install-meta.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _script_candidates(page_text: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"https?://[^\s\"'<>]+(?:\.ps1|\.sh)", page_text, flags=re.I):
        urls.append(match.rstrip(").,;"))
    for match in re.findall(r"(?:href|src)=[\"']([^\"']+(?:\.ps1|\.sh))[\"']", page_text, flags=re.I):
        urls.append(urljoin(base_url, match))
    fallback = "node.ps1" if os.name == "nt" else "node.sh"
    urls.append(urljoin(base_url, fallback))
    deduped: list[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _download_installer(page_url: str, page_text: str, report: dict) -> Path | None:
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".ps1" if os.name == "nt" else ".sh"
    for candidate in _script_candidates(page_text, page_url):
        if os.name == "nt" and not candidate.lower().endswith(".ps1"):
            continue
        if os.name != "nt" and not candidate.lower().endswith(".sh"):
            continue
        status, body, error = fetch_text(candidate)
        report.setdefault("installer_candidates", []).append({"url": candidate, "status": status, "error": error})
        if status and 200 <= status < 400 and body.strip():
            path = INSTALLER_DIR / f"get-urirun-installer{suffix}"
            path.write_text(body, encoding="utf-8", errors="replace")
            report["installer_url"] = candidate
            report["installer_path"] = str(path)
            report["installer_sha256"] = sha256_file(path)
            report["installer_excerpt"] = body[:4000]
            return path
    return None


def _run_post_install_checks(executable: str, env: dict[str, str], report: dict) -> None:
    version = run_capture([executable, "--version"], env=env, timeout=60)
    doctor = run_capture([executable, "doctor", "--json"], env=env, timeout=90)
    basic = run_capture([executable, "--help"], env=env, timeout=60)
    report["urirun_executable"] = executable
    report["urirun_version_result"] = {
        "exit_code": version.returncode,
        "stdout": version.stdout,
        "stderr": version.stderr,
    }
    report["urirun_doctor_result"] = {
        "exit_code": doctor.returncode,
        "stdout": doctor.stdout,
        "stderr": doctor.stderr,
    }
    report["basic_cli_result"] = {
        "exit_code": basic.returncode,
        "stdout": basic.stdout,
        "stderr": basic.stderr,
    }
    assert version.returncode == 0
    assert doctor.returncode == 0
    assert basic.returncode == 0


def _local_repo_install(report: dict) -> None:
    meta = _load_install_meta()
    source = Path(os.environ.get("URIRUN_SOURCE_DIR") or meta.get("source") or "")
    python_pkg = source / "adapters" / "python"
    if not python_pkg.exists():
        pytest.xfail("No local urirun source is available for GET_URIRUN_INSTALL_MODE=local-repo.")
    venv = WORK / "user-install-venv"
    if venv.exists():
        shutil.rmtree(venv)
    subprocess.run([sys.executable, "-m", "venv", str(venv)], cwd=ROOT, check=True)
    py = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    env = isolated_env(isolated_home("user-install-home"))
    pip_install = run_capture([str(py), "-m", "pip", "install", str(python_pkg)], env=env, timeout=180)
    report["executed_command"] = [str(py), "-m", "pip", "install", str(python_pkg)]
    report["exit_code"] = pip_install.returncode
    report["stdout"] = pip_install.stdout
    report["stderr"] = pip_install.stderr
    if pip_install.returncode != 0:
        write_json_report("get-urirun-install.json", report)
    assert pip_install.returncode == 0
    exe = venv / ("Scripts" if os.name == "nt" else "bin") / ("urirun.exe" if os.name == "nt" else "urirun")
    report["installed_location"] = str(exe)
    _run_post_install_checks(str(exe), env, report)


def _remote_site_install(installer: Path, report: dict) -> None:
    home = isolated_home("remote-installer-home")
    env = isolated_env(home)
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            pytest.skip("PowerShell is required for the Windows installer flow.")
        command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer)]
    else:
        shell = shutil.which("bash")
        if not shell:
            pytest.skip("bash is required for the Linux/macOS installer flow.")
        command = [shell, str(installer)]
    result = run_capture(command, env=env, timeout=300)
    report["executed_command"] = command
    report["exit_code"] = result.returncode
    report["stdout"] = result.stdout
    report["stderr"] = result.stderr
    executable = find_executable("urirun", env)
    report["installed_location"] = executable
    if result.returncode != 0 or not executable:
        write_json_report("get-urirun-install.json", report)
    assert result.returncode == 0
    assert executable, "urirun was not found on PATH after installer execution"
    _run_post_install_checks(executable, env, report)


@pytest.mark.user_journey
@pytest.mark.experimental
def test_get_urirun_user_install_flow():
    mode = os.environ.get("GET_URIRUN_INSTALL_MODE", "site")
    if mode == "skip":
        pytest.skip("GET_URIRUN_INSTALL_MODE=skip")
    page_url = os.environ.get("GET_URIRUN_PRODUCTION_URL") or os.environ.get("GET_URIRUN_URL", "https://get.urirun.com/")
    allow_remote = os.environ.get("GET_URIRUN_ALLOW_REMOTE_INSTALL", "0") == "1"
    report = {
        "platform": platform.platform(),
        "system": current_system(),
        "page_url": page_url,
        "install_mode": mode,
        "allow_remote_install": allow_remote,
        "detected_install_command": None,
        "installer_url": None,
        "installer_path": None,
        "installer_sha256": None,
        "executed_command": None,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "installed_location": None,
        "urirun_version_result": None,
        "urirun_doctor_result": None,
        "recommendation": "Run with GET_URIRUN_ALLOW_REMOTE_INSTALL=1 in CI to execute the downloaded installer, or use GET_URIRUN_INSTALL_MODE=local-repo for a safe local-source installation.",
    }
    status, page_text, page_error = fetch_text(page_url)
    report["page_status"] = status
    report["page_error"] = page_error
    report["detected_install_command"] = "\n".join(
        line.strip() for line in page_text.splitlines()
        if "urirun" in line.lower() and ("curl" in line.lower() or "powershell" in line.lower() or ".ps1" in line.lower() or ".sh" in line.lower())
    )[:2000] or None

    if mode == "local-repo":
        try:
            _local_repo_install(report)
        finally:
            write_json_report("get-urirun-install.json", report)
        return

    if mode != "site":
        pytest.fail(f"unsupported GET_URIRUN_INSTALL_MODE={mode!r}")

    installer = _download_installer(page_url, page_text, report)
    if installer is None:
        write_json_report("get-urirun-install.json", report)
        pytest.xfail("No platform installer script could be detected or downloaded from get.urirun.com.")

    if not allow_remote:
        write_json_report("get-urirun-install.json", report)
        pytest.xfail("Remote installer execution is disabled by GET_URIRUN_ALLOW_REMOTE_INSTALL=0; script was downloaded and hashed only.")

    try:
        _remote_site_install(installer, report)
    finally:
        write_json_report("get-urirun-install.json", report)
