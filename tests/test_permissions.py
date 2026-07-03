from __future__ import annotations

import pytest

from tests.conftest import run_cmd


@pytest.mark.stable
def test_execute_without_allow_is_denied(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/echo/query/text",
        registry_path,
        "--payload",
        "{\"text\":\"blocked\"}",
        "--execute",
    ], check=False)
    text = (cp.stdout + cp.stderr).lower()
    assert cp.returncode != 0
    assert "allow" in text or "permission" in text or "policy" in text


@pytest.mark.stable
def test_wrong_allow_list_is_denied(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/echo/query/text",
        registry_path,
        "--payload",
        "{\"text\":\"blocked\"}",
        "--execute",
        "--allow",
        "other://**",
    ], check=False)
    assert cp.returncode != 0
    assert "blocked" not in cp.stdout
