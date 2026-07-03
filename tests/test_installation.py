from __future__ import annotations

import json

import pytest

from tests.conftest import run_cmd, urirun_version


@pytest.mark.stable
def test_urirun_cli_version_is_available():
    version = urirun_version()
    assert version.startswith("urirun ")


@pytest.mark.stable
def test_urirun_doctor_reports_ok(cli):
    cp = run_cmd([cli, "doctor", "--json"])
    data = json.loads(cp.stdout)
    assert data["ok"] is True
    assert data["version"]
    assert data["interpreter"]


@pytest.mark.stable
def test_validate_fixture_registry(cli, registry_path):
    cp = run_cmd([cli, "validate", registry_path, "--json"])
    data = json.loads(cp.stdout)
    assert data.get("ok") is True
