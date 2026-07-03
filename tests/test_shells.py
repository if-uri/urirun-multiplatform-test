from __future__ import annotations

import os
import shlex
import shutil

import pytest

from tests.conftest import command_path, run_cmd, run_shell


def _quote_for_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@pytest.mark.stable
def test_python_and_urirun_are_on_test_path_from_subprocess(python_executable):
    cp = run_cmd(
        [python_executable, "-c", "import shutil; print(shutil.which('urirun') or '')"],
        timeout=30,
    )
    assert cp.returncode == 0
    assert "urirun" in cp.stdout.lower()


@pytest.mark.stable
def test_bash_can_run_urirun_version_when_available():
    bash = shutil.which("bash")
    if os.name == "nt" and bash and "system32" in bash.lower():
        pytest.skip("Windows system32 bash is the WSL launcher and may not see the Windows test venv")
    cli = command_path("urirun")
    command = f"{shlex.quote(cli)} --version"
    cp = run_shell(command, shell_name="bash")
    assert "urirun " in (cp.stdout + cp.stderr)


@pytest.mark.stable
def test_powershell_can_run_urirun_version_when_available():
    cli = command_path("urirun")
    if not (shutil.which("pwsh") or shutil.which("powershell")):
        pytest.skip("PowerShell is not available on this runner")
    cp = run_shell(f"& {_quote_for_powershell(cli)} --version", shell_name="powershell")
    assert "urirun " in (cp.stdout + cp.stderr)


@pytest.mark.stable
@pytest.mark.skipif(os.name != "nt", reason="cmd.exe is Windows-only")
def test_cmd_can_run_urirun_version_on_windows():
    cp = run_shell("urirun --version", shell_name="cmd")
    assert "urirun " in (cp.stdout + cp.stderr)
