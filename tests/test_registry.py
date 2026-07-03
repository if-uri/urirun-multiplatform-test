from __future__ import annotations

import pytest

from tests.conftest import run_cmd


@pytest.mark.stable
def test_compile_fixture_registry(cli, registry_path, tmp_path):
    out = tmp_path / "compiled-registry.json"
    cp = run_cmd([cli, "compile", registry_path, "--out", str(out)])
    assert cp.returncode == 0
    assert out.exists()
    assert "demo://local/echo/query/text" in out.read_text(encoding="utf-8")


@pytest.mark.stable
def test_urirun_run_executes_registry_route(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/echo/query/text",
        registry_path,
        "--payload",
        "{\"text\":\"hello-multiplatform\"}",
        "--execute",
        "--allow",
        "demo://**",
    ])
    assert "hello-multiplatform" in cp.stdout
    assert "\"ok\"" in cp.stdout or "'ok'" in cp.stdout


@pytest.mark.stable
def test_bad_uri_returns_nonzero(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/missing/query/nope",
        registry_path,
        "--payload",
        "{}",
        "--execute",
        "--allow",
        "demo://**",
    ], check=False)
    assert cp.returncode != 0
    assert "not" in (cp.stdout + cp.stderr).lower() or "error" in (cp.stdout + cp.stderr).lower()
