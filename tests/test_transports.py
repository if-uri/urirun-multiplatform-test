from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pytest

from tests.conftest import command_path, run_cmd, urirun_version, xfail_if_mesh_unavailable
from tests.process_utils import free_tcp_port, run_client, start_process, transport_env, wait_for_port_or_process, write_transport_report


def _policy_file(tmp_path: Path) -> Path:
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"execute": {"allow": ["demo://**"]}, "timeout": 10}), encoding="utf-8")
    return policy


def _python_module_command(module: str, *args: str) -> list[str]:
    return [command_path("python"), "-m", module, *args]


@pytest.mark.stable
def test_http_node_transport_run_roundtrip(registry_path, tmp_path):
    host = "127.0.0.1"
    port = free_tcp_port(host)
    server_command = [
        command_path("urirun"),
        "node",
        "serve",
        "--registry",
        registry_path,
        "--host",
        host,
        "--port",
        str(port),
        "--execute",
        "--allow",
        "demo://**",
    ]
    server = start_process("transport-http-node", server_command)
    client_result = None
    try:
        try:
            wait_for_port_or_process(host, port, server, timeout=60)
        except RuntimeError as exc:
            xfail_if_mesh_unavailable(str(exc))
            raise
        health = urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5)
        assert health.status == 200
        body = json.dumps({
            "uri": "demo://local/echo/query/text",
            "payload": {"text": "http-transport"},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"http://{host}:{port}/run",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        response = urllib.request.urlopen(request, timeout=15)
        payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        assert "http-transport" in json.dumps(payload)
    except Exception:
        write_transport_report(
            "transport-http-node",
            transport="http",
            host=host,
            port=port,
            server_command=server_command,
            client_command=["POST", f"http://{host}:{port}/run"],
            server_logs=server.read_logs(),
            client_result=client_result,
            urirun_version=urirun_version(best_effort=True),
            recommendation="Check that urirun node serve starts, /health returns 200, and /run accepts the fixture registry.",
        )
        raise
    finally:
        server.terminate()


@pytest.mark.experimental
def test_mcp_stdio_transport_tools_call(registry_path, tmp_path):
    policy = _policy_file(tmp_path)
    tools_command = _python_module_command("urirun.runtime.v2_mcp", "tools", registry_path)
    tools = run_client(tools_command)
    if tools.returncode != 0:
        write_transport_report(
            "transport-mcp-tools",
            transport="mcp",
            host="stdio",
            port=None,
            server_command=None,
            client_command=tools_command,
            server_logs=None,
            client_result=tools,
            urirun_version=urirun_version(best_effort=True),
            recommendation="Check that urirun.runtime.v2_mcp imports and can project fixture registry tools.",
        )
    assert tools.returncode == 0
    manifest = json.loads(tools.stdout)
    tool_name = next(tool["name"] for tool in manifest["tools"] if "echo" in tool["name"])
    requests = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": {"text": "mcp-transport"}},
        }),
        "",
    ])
    server_command = _python_module_command("urirun.runtime.v2_mcp", "serve", registry_path, "--execute", "--policy", str(policy))
    result = None
    try:
        import subprocess

        result = subprocess.run(
            server_command,
            input=requests,
            cwd=Path(__file__).resolve().parents[1],
            env=transport_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=20,
        )
        assert result.returncode == 0
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        call = next(line for line in lines if line.get("id") == 2)
        envelope = json.loads(call["result"]["content"][0]["text"])
        assert envelope["ok"] is True
        assert "mcp-transport" in json.dumps(envelope)
    except Exception:
        write_transport_report(
            "transport-mcp-stdio",
            transport="mcp",
            host="stdio",
            port=None,
            server_command=server_command,
            client_command=["JSON-RPC", "tools/call", tool_name],
            server_logs={"stdout": "" if result is None else result.stdout, "stderr": "" if result is None else result.stderr},
            client_result=result,
            urirun_version=urirun_version(best_effort=True),
            recommendation="Check MCP JSON-RPC framing, policy allow-list, and that the selected tool maps to the fixture echo URI.",
        )
        raise


@pytest.mark.experimental
def test_grpc_transport_run_roundtrip(registry_path, tmp_path):
    grpc_check = run_client([command_path("python"), "-c", "import grpc; print(grpc.__version__)"])
    if grpc_check.returncode != 0:
        pytest.xfail("gRPC transport requires optional dependency grpcio; current base install does not guarantee it.")

    host = "127.0.0.1"
    port = free_tcp_port(host)
    policy = _policy_file(tmp_path)
    server_command = _python_module_command(
        "urirun.runtime.v2_grpc",
        "serve",
        registry_path,
        "--host",
        host,
        "--port",
        str(port),
        "--policy",
        str(policy),
        "--execute",
    )
    server = start_process("transport-grpc", server_command)
    client_command = _python_module_command(
        "urirun.runtime.v2_grpc",
        "call",
        "demo://local/echo/query/text",
        registry_path,
        "--target",
        "local",
        "--payload",
        json.dumps({"text": "grpc-transport"}),
        "--execute",
    )
    client_result = None
    try:
        wait_for_port_or_process(host, port, server, timeout=60)
        env = transport_env({"URI_GRPC_MAP": json.dumps({"local": f"{host}:{port}"})})
        client_result = run_client(client_command, env=env, timeout=30)
        assert client_result.returncode == 0
        payload = json.loads(client_result.stdout)
        assert payload["ok"] is True
        assert "grpc-transport" in json.dumps(payload)
    except Exception:
        write_transport_report(
            "transport-grpc",
            transport="grpc",
            host=host,
            port=port,
            server_command=server_command,
            client_command=client_command,
            server_logs=server.read_logs(),
            client_result=client_result,
            urirun_version=urirun_version(best_effort=True),
            recommendation="Install urirun[grpc] or grpcio, verify URI_GRPC_MAP points at the test server, and inspect server logs.",
        )
        raise
    finally:
        server.terminate()
