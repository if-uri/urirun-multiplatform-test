"""Host mesh smoke tests: `urirun host` must work on a fresh install.

A fresh `pip install` of urirun currently pulls no `urirun_flow` (the
dependency chain urirun-contract -> urirun-connector-router -> urirun-flow
is not published on PyPI), which makes every `urirun host`/`urirun node`
command answer `{"ok": false, "error": "mesh not available"}` while the
rest of the CLI keeps working. These tests keep that regression visible.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import run_cmd, xfail_if_mesh_unavailable
from tests.process_utils import free_tcp_port, start_process, transport_env, wait_for_port_or_process

def _mesh_or_xfail(cp) -> str:
    output = cp.stdout + cp.stderr
    xfail_if_mesh_unavailable(output)
    return output


@pytest.mark.stable
def test_host_mesh_layer_is_available_after_install(cli, tmp_path):
    config = tmp_path / "mesh.json"
    cp = run_cmd([cli, "host", "init", "--config", str(config)], check=False)
    _mesh_or_xfail(cp)
    assert cp.returncode == 0, cp.stderr
    assert config.exists()
    document = json.loads(config.read_text(encoding="utf-8"))
    assert document.get("version") == "urirun.mesh.v1"


@pytest.mark.stable
def test_host_mesh_works_without_source_pythonpath(cli, tmp_path):
    """The end-user state: installed package only, no source tree on PYTHONPATH.

    The harness compensates for the --no-deps install fallback by exporting the
    urirun source checkout on PYTHONPATH, which also makes the excluded
    `urirun_flow` package importable. A real `pip install urirun` gets no such
    help, so mesh availability must be probed with a clean PYTHONPATH too.
    """
    import os
    import subprocess

    config = tmp_path / "mesh.json"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("PYTHONUTF8", "1")
    cp = subprocess.run(
        [cli, "host", "init", "--config", str(config)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=60,
    )
    _mesh_or_xfail(cp)
    assert cp.returncode == 0, cp.stderr
    assert config.exists()


@pytest.mark.stable
def test_host_discovers_node_and_dispatches_uri(cli, registry_path, tmp_path):
    config = tmp_path / "mesh.json"
    init = run_cmd([cli, "host", "init", "--config", str(config)], check=False)
    _mesh_or_xfail(init)

    host = "127.0.0.1"
    port = free_tcp_port(host)
    server_command = [
        cli,
        "node",
        "serve",
        "--registry",
        registry_path,
        "--name",
        "meshnode",
        "--host",
        host,
        "--port",
        str(port),
        "--execute",
        "--allow",
        "demo://*",
    ]
    server = start_process("mesh-host-node", server_command, env=transport_env())
    try:
        wait_for_port_or_process(host, port, server, timeout=60)

        added = run_cmd(
            [cli, "host", "add-node", "meshnode", f"http://{host}:{port}", "--kind", "server", "--config", str(config)]
        )
        assert '"ok": true' in added.stdout

        nodes = run_cmd([cli, "host", "nodes", "--config", str(config)])
        assert "meshnode" in nodes.stdout
        assert "up" in nodes.stdout

        dispatched = run_cmd(
            [
                cli,
                "host",
                "run",
                "meshnode",
                "demo://local/echo/query/text",
                "--config",
                str(config),
                "--payload",
                json.dumps({"text": "mesh-roundtrip"}),
            ]
        )
        result = json.loads(dispatched.stdout)
        assert result["ok"] is True
        assert "mesh-roundtrip" in result["result"]["stdout"]
    finally:
        server.terminate()
