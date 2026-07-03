from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.conftest import REPORT_DIR, run_cmd, write_failure_report


@pytest.mark.stable
def test_failing_route_is_reported(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/fail/command/boom",
        registry_path,
        "--payload",
        "{}",
        "--execute",
        "--allow",
        "demo://**",
    ], check=False)
    assert cp.returncode != 0
    report = write_failure_report("intentional_failing_route", [cli, "run", "demo://local/fail/command/boom"], cp)
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["exit_code"] == cp.returncode
    assert "fixture boom" in data["stderr"] or "fixture boom" in data["stdout"]
    assert data["system"]["os"]
    assert data["urirun"]
    assert data["recommendation"]


@pytest.mark.stable
def test_urirun_error_log_is_created_for_policy_denial(cli, registry_path):
    error_log = REPORT_DIR / "urirun-errors.jsonl"
    if error_log.exists():
        error_log.unlink()
    cp = run_cmd([
        cli,
        "run",
        "demo://local/echo/query/text",
        registry_path,
        "--payload",
        "{\"text\":\"denied\"}",
        "--execute",
    ], check=False)
    assert cp.returncode != 0
    assert error_log.exists() or "error://" in (cp.stdout + cp.stderr)


@pytest.mark.expected_failure
@pytest.mark.xfail(reason="Full stack traces depend on the current urirun CLI error envelope.")
def test_error_cli_exposes_stack_trace_for_process_failures(cli, registry_path):
    cp = run_cmd([
        cli,
        "run",
        "demo://local/fail/command/boom",
        registry_path,
        "--payload",
        "{}",
        "--execute",
        "--allow",
        "demo://**",
    ], check=False)
    assert "traceback" in (cp.stdout + cp.stderr).lower()
