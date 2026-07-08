from __future__ import annotations

import json

import pytest

from tests.conftest import run_cmd, xfail_if_mesh_unavailable


@pytest.mark.stable
def test_tree_json_renders_fixture_registry(cli, registry_path):
    cp = run_cmd([cli, "tree", registry_path, "--format", "json"])
    data = json.loads(cp.stdout)
    assert data["uri_tree"]["demo"]["local"]["echo"]["query"]["text"]["uri"] == "demo://local/echo/query/text"


@pytest.mark.stable
def test_agent_space_lists_fixture_routes(cli, registry_path):
    cp = run_cmd([cli, "agent", "space", registry_path])
    assert "demo://local/echo/query/text" in cp.stdout


@pytest.mark.stable
def test_errors_bindings_compile_and_list(cli, tmp_path):
    bindings = tmp_path / "error-bindings.json"
    registry = tmp_path / "error-registry.json"
    cp = run_cmd([cli, "errors", "bindings"])
    assert "error://local/errors/query" in cp.stdout
    bindings.write_text(cp.stdout, encoding="utf-8")
    run_cmd([cli, "compile", str(bindings), "--out", str(registry)])
    listed = run_cmd([cli, "list", str(registry)])
    assert "error://local/errors/query/recent" in listed.stdout or "error://local/errors/query" in listed.stdout


@pytest.mark.stable
def test_discover_entry_points_outputs_bindings(cli, tmp_path):
    out = tmp_path / "discovered.json"
    cp = run_cmd([cli, "discover", "--out", str(out), "--generated-at", "2026-07-03T00:00:00Z"])
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "urirun.bindings.v2"
    assert "bindings" in data


@pytest.mark.stable
def test_gen_openapi_from_fixture_registry(cli, registry_path, tmp_path):
    out = tmp_path / "openapi.json"
    cp = run_cmd([cli, "gen", "openapi", registry_path, "--out", str(out), "--title", "urirun E2E"])
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")
    assert "paths" in data


@pytest.mark.stable
def test_add_command_generates_portable_binding(cli, tmp_path):
    out = tmp_path / "added.bindings.json"
    cp = run_cmd([
        cli,
        "add-command",
        "demo://local/generated/query/ping",
        "--argv",
        "python -c \"print('generated-pong')\"",
        "--out",
        str(out),
    ])
    assert cp.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "demo://local/generated/query/ping" in text


@pytest.mark.stable
def test_node_config_roundtrip_without_starting_service(cli, registry_path, tmp_path):
    config = tmp_path / "node.json"
    init = run_cmd([
        cli,
        "node",
        "init",
        "--config",
        str(config),
        "--name",
        "e2e-node",
        "--registry",
        registry_path,
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
    ], check=False)
    xfail_if_mesh_unavailable(init.stdout + init.stderr)
    assert init.returncode == 0, init.stderr
    cp = run_cmd([cli, "node", "config", "--config", str(config)])
    assert "e2e-node" in cp.stdout
    assert "127.0.0.1" in cp.stdout


@pytest.mark.stable
def test_host_config_roundtrip_without_network(cli, tmp_path):
    config = tmp_path / "mesh.json"
    init = run_cmd([cli, "host", "init", "--config", str(config), "--name", "e2e-host"], check=False)
    xfail_if_mesh_unavailable(init.stdout + init.stderr)
    assert init.returncode == 0, init.stderr
    run_cmd([cli, "host", "add-node", "--config", str(config), "local", "http://127.0.0.1:8765", "--kind", "api"])
    cp = run_cmd([cli, "host", "config", "--config", str(config)])
    assert "e2e-host" in cp.stdout
    assert "127.0.0.1:8765" in cp.stdout


@pytest.mark.experimental
def test_compat_list_is_callable(cli):
    cp = run_cmd([cli, "compat", "list"], check=False)
    assert cp.returncode in (0, 1)
    assert cp.stdout or cp.stderr
