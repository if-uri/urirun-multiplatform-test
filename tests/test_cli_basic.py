from __future__ import annotations

import pytest

from tests.conftest import run_cmd


@pytest.mark.stable
def test_help_lists_core_commands(cli):
    cp = run_cmd([cli, "--help"])
    for word in ("run", "connectors", "validate", "compile", "doctor", "scan", "gen", "agent", "host", "node"):
        assert word in cp.stdout


@pytest.mark.stable
def test_list_routes_from_fixture_registry(cli, registry_path):
    cp = run_cmd([cli, "list", registry_path])
    assert "demo://local/echo/query/text" in cp.stdout
    assert "demo://local/fail/command/boom" in cp.stdout


@pytest.mark.stable
def test_bad_command_returns_nonzero(cli):
    cp = run_cmd([cli, "definitely-not-a-real-command"], check=False)
    assert cp.returncode != 0
    assert "usage:" in (cp.stderr + cp.stdout).lower()


@pytest.mark.stable
def test_version_subcommand_skips_network_check(cli):
    cp = run_cmd([cli, "version", "--no-check", "--json"])
    text = cp.stdout.strip()
    assert text.startswith("{") and "version" in text or text.count(".") >= 1


@pytest.mark.stable
@pytest.mark.parametrize("command", ["doctor", "scan", "compile", "discover", "validate", "gen", "connectors", "agent", "errors", "compat", "host", "node"])
def test_subcommands_expose_help(cli, command):
    cp = run_cmd([cli, command, "--help"])
    assert cp.returncode == 0
    assert "usage:" in cp.stdout.lower()
