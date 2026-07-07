from __future__ import annotations

import json

from tests.deployment_bundle import (
    artifact_record,
    build_manifest,
    create_deployment_bundle,
    diff_manifests,
    parse_sha256sums,
    validate_bundle,
    validate_sha256sums,
)


def test_deployment_bundle_structure_and_checksums(tmp_path):
    artifact_dir = tmp_path / "artifacts-in"
    artifact_dir.mkdir()
    wheel = artifact_dir / "urirun-1.0.0-py3-none-any.whl"
    sdist = artifact_dir / "urirun-1.0.0.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    records = [artifact_record(wheel), artifact_record(sdist)]
    manifest = build_manifest(
        product="urirun",
        version="1.0.0",
        repo_url="https://github.com/if-uri/urirun.git",
        ref="main",
        revision="abc123",
        artifacts=records,
    )

    bundle_dir = tmp_path / "deployment-bundle"
    report = create_deployment_bundle(artifact_dir=artifact_dir, bundle_dir=bundle_dir, manifest=manifest, artifacts=records)

    assert report["promotion_candidate"] is True
    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "artifacts" / wheel.name).exists()
    assert (bundle_dir / "checksums" / "SHA256SUMS").exists()
    assert (bundle_dir / "site" / "index.html").exists()
    assert (bundle_dir / "deployment-report.json").exists()
    assert validate_sha256sums(bundle_dir) == []
    assert validate_bundle(bundle_dir)["status"] == "DONE"

    sums = parse_sha256sums(bundle_dir / "checksums" / "SHA256SUMS")
    assert set(sums) == {f"artifacts/{wheel.name}", f"artifacts/{sdist.name}"}


def test_manifest_records_future_platform_artifacts(tmp_path):
    wheel = tmp_path / "urirun-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    manifest = build_manifest(product="urirun", version="1.0.0", repo_url=None, ref="main", revision=None, artifacts=[artifact_record(wheel)])
    future_kinds = {item["kind"] for item in manifest["future_artifacts"]}
    assert "windows-exe" in future_kinds
    assert "macos-pkg" in future_kinds
    assert all(item["status"] == "EXTERNAL BLOCKER" for item in manifest["future_artifacts"])


def test_manifest_diff_report():
    local = {
        "version": "1",
        "ref": "main",
        "revision": "a",
        "artifacts": [{"name": "a.whl", "sha256": "111"}, {"name": "b.tar.gz", "sha256": "222"}],
    }
    production = {
        "version": "2",
        "ref": "main",
        "revision": "b",
        "artifacts": [{"name": "a.whl", "sha256": "999"}, {"name": "old.exe", "sha256": "333"}],
    }
    diff = diff_manifests(local, production)
    assert diff["version"]["matches"] is False
    assert diff["missing_in_production"] == ["b.tar.gz"]
    assert diff["missing_locally"] == ["old.exe"]
    assert diff["checksum_differences"] == ["a.whl"]
