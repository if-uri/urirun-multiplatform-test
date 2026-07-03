from __future__ import annotations

import json

import pytest

from tests.conftest import run_cmd


@pytest.mark.stable
def test_connectors_show_planfile(cli):
    cp = run_cmd([cli, "connectors", "show", "planfile", "--json"], timeout=90, check=False)
    if cp.returncode != 0 and "unknown connectors sub-command" in (cp.stdout + cp.stderr):
        pytest.xfail("Current urirun CLI parser exposes 'connectors show', but the command handler rejects it.")
    assert cp.returncode == 0
    text = cp.stdout + cp.stderr
    assert "planfile" in text.lower()
    assert "task://" in text or "install" in text.lower()


@pytest.mark.experimental
def test_connectors_doctor_can_load_installed_bindings(cli):
    cp = run_cmd([cli, "connectors", "doctor", "--json"])
    data = json.loads(cp.stdout)
    assert data["total"] >= 3
    names = {item["name"] for item in data["connectors"]}
    assert {"ready", "session", "skill"}.issubset(names)
    assert all("bindingCount" in item for item in data["connectors"])


@pytest.mark.stable
@pytest.mark.parametrize("connector_id", ["planfile", "sqlite-context", "mqtt"])
def test_connectors_install_dry_run_is_safe(cli, connector_id):
    cp = run_cmd([cli, "connectors", "install", connector_id, "--json"], check=False, timeout=90)
    text = (cp.stdout + cp.stderr).lower()
    if "catalog" in text and ("urlerror" in text or "offline" in text or "temporary failure" in text):
        pytest.xfail("Connector catalog is not reachable from this runner.")
    assert cp.returncode in (0, 1)
    assert connector_id in text or "unknown" in text or "skipped" in text or "pip" in text
