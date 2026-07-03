from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.conftest import ROOT, run_cmd


@pytest.mark.stable
def test_registry_file_path_accepts_native_separators(cli, registry_path):
    native = str(Path(registry_path))
    assert ("\\" in native) == (os.name == "nt")
    cp = run_cmd([cli, "list", native])
    assert "demo://local/path/query/roundtrip" in cp.stdout


@pytest.mark.stable
def test_run_preserves_path_with_spaces_and_unicode(cli, registry_path, tmp_path):
    nested = tmp_path / "dir with spaces"
    nested.mkdir()
    sample = nested / "zazolc file name.txt"
    sample.write_text("hello path", encoding="utf-8")
    cp = run_cmd([
        cli,
        "run",
        "demo://local/path/query/roundtrip",
        registry_path,
        "--payload",
        json.dumps({"path": str(sample)}),
        "--execute",
        "--allow",
        "demo://**",
    ])
    assert "zazolc file name.txt" in cp.stdout
    assert "true" in cp.stdout.lower()


@pytest.mark.stable
def test_relative_registry_path_from_workspace(cli):
    cp = run_cmd([cli, "list", "fixtures/registry.json"], cwd=ROOT)
    assert "demo://local/echo/query/text" in cp.stdout


@pytest.mark.stable
def test_output_paths_can_be_in_directory_with_spaces(cli, registry_path, tmp_path):
    out_dir = tmp_path / "compiled output"
    out_dir.mkdir()
    out = out_dir / "registry with spaces.json"
    run_cmd([cli, "compile", registry_path, "--out", str(out)])
    assert out.exists()
    assert "demo://local/cwd/query/show" in out.read_text(encoding="utf-8")
