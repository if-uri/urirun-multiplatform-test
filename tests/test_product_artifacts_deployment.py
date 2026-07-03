from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import pytest

from tests.gui_utils import current_system, fetch_text, write_json_report


pytestmark = pytest.mark.skipif(
    os.environ.get("URIRUN_USER_JOURNEY_ACTIVE") != "1",
    reason="user journey tests run only in installer-gui-e2e/user-journey profile or when explicitly targeted through scripts/run_tests.py",
)


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"
REPORT_DIR = ROOT / "reports"
DEFAULT_PRODUCTION_URL = "https://get.urirun.com/"


def _install_meta() -> dict:
    path = WORK / "install-meta.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _source_dir() -> Path:
    source = os.environ.get("URIRUN_SOURCE_DIR") or _install_meta().get("source")
    if not source:
        pytest.xfail("No urirun source checkout is available to build product artifacts.")
    path = Path(source)
    if not (path / "adapters" / "python" / "pyproject.toml").exists():
        pytest.xfail(f"urirun source checkout does not contain adapters/python/pyproject.toml: {path}")
    return path


def _artifact_dir() -> Path:
    configured = os.environ.get("URIRUN_ARTIFACTS_DIR")
    path = Path(configured) if configured else REPORT_DIR / "product-artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_python_artifacts(source: Path, artifact_dir: Path) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
    package_dir = source / "adapters" / "python"
    dist_dir = package_dir / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    result = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(artifact_dir)],
        cwd=package_dir,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=240,
    )
    artifacts = []
    for path in sorted(artifact_dir.glob("urirun-*")):
        if path.is_file() and path.suffix in {".whl", ".gz", ".zip", ".exe"}:
            artifacts.append({
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
                "kind": "wheel" if path.suffix == ".whl" else "sdist" if path.name.endswith(".tar.gz") else path.suffix.lstrip("."),
                "platform": "python-any" if "py3-none-any" in path.name else "source",
            })
    return result, artifacts


def _write_manifest(artifact_dir: Path, artifacts: list[dict]) -> Path:
    meta = _install_meta()
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "product": "urirun",
        "version": None,
        "repo_url": meta.get("repo_url") or os.environ.get("URIRUN_REPO_URL"),
        "ref": meta.get("ref") or os.environ.get("URIRUN_REF"),
        "revision": meta.get("revision"),
        "artifacts": artifacts,
    }
    version_file = _source_dir() / "VERSION"
    if version_file.exists():
        manifest["version"] = version_file.read_text(encoding="utf-8").strip()
    path = artifact_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _simulate_local_deployment(artifact_dir: Path, artifacts: list[dict]) -> Path:
    deploy_dir = REPORT_DIR / "local-deployment"
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir(parents=True, exist_ok=True)
    public_dir = deploy_dir / "artifacts"
    public_dir.mkdir(parents=True, exist_ok=True)
    for item in artifacts:
        shutil.copy2(item["path"], public_dir / item["name"])
    manifest = _write_manifest(public_dir, [
        {**item, "url": f"/artifacts/{item['name']}"} for item in artifacts
    ])
    index = deploy_dir / "index.html"
    links = "\n".join(
        f'<li><a href="artifacts/{item["name"]}">{item["name"]}</a></li>' for item in artifacts
    )
    index.write_text(
        "<!doctype html><title>get urirun local deployment</title>"
        "<h1>urirun local deployment simulation</h1>"
        f'<p><a href="artifacts/{manifest.name}">manifest.json</a></p><ul>{links}</ul>',
        encoding="utf-8",
    )
    return deploy_dir


def _production_artifact_refs(text: str, base_url: str) -> list[str]:
    refs = []
    for token in text.replace('"', " ").replace("'", " ").split():
        clean = token.strip("()[]{}<>,;")
        lower = clean.lower()
        if any(lower.endswith(suffix) for suffix in (".exe", ".whl", ".tar.gz", ".zip", ".ps1", ".sh", "manifest.json")):
            refs.append(urljoin(base_url, clean))
    return sorted(set(refs))


@pytest.mark.user_journey
@pytest.mark.experimental
def test_build_product_artifacts_and_local_deployment_simulation():
    deployment_mode = os.environ.get("URIRUN_DEPLOYMENT_MODE", "local-simulated")
    artifact_dir = _artifact_dir()
    report = {
        "system": current_system(),
        "deployment_mode": deployment_mode,
        "source": str(_source_dir()),
        "product_artifacts_dir": str(artifact_dir),
        "product_artifacts": [],
        "diagnostic_artifacts": {
            "report": str(REPORT_DIR / "product-artifacts-deployment.json"),
        },
        "build_command": None,
        "build_exit_code": None,
        "build_stdout": "",
        "build_stderr": "",
        "local_deployment_dir": None,
        "local_deployment_manifest": None,
        "external_requirements": [],
        "recommendation": "Use URIRUN_DEPLOYMENT_MODE=local-simulated for CI-safe validation; wire production deployment only in trusted CI with explicit credentials.",
    }
    if deployment_mode == "skip":
        write_json_report("product-artifacts-deployment.json", report)
        pytest.skip("URIRUN_DEPLOYMENT_MODE=skip")
    if deployment_mode == "production":
        report["external_requirements"].append("Production deployment requires secrets/permissions and is intentionally not executed by this harness.")
        write_json_report("product-artifacts-deployment.json", report)
        pytest.xfail("Production deployment is an external CI/CD requirement; this test does not deploy to production.")

    source = _source_dir()
    command = [sys.executable, "-m", "build", "--outdir", str(artifact_dir)]
    result, artifacts = _build_python_artifacts(source, artifact_dir)
    report["build_command"] = command
    report["build_exit_code"] = result.returncode
    report["build_stdout"] = result.stdout
    report["build_stderr"] = result.stderr
    report["product_artifacts"] = artifacts
    if result.returncode != 0:
        write_json_report("product-artifacts-deployment.json", report)
    assert result.returncode == 0
    assert any(item["kind"] == "wheel" for item in artifacts)
    assert any(item["kind"] == "sdist" for item in artifacts)

    deploy_dir = _simulate_local_deployment(artifact_dir, artifacts)
    report["local_deployment_dir"] = str(deploy_dir)
    report["local_deployment_manifest"] = str(deploy_dir / "artifacts" / "manifest.json")
    write_json_report("product-artifacts-deployment.json", report)


@pytest.mark.user_journey
@pytest.mark.experimental
def test_production_and_local_dev_site_artifact_references():
    mode = os.environ.get("GET_URIRUN_SITE_MODE", "production-site")
    production_url = os.environ.get("GET_URIRUN_PRODUCTION_URL") or os.environ.get("GET_URIRUN_URL", DEFAULT_PRODUCTION_URL)
    report = {
        "system": current_system(),
        "site_mode": mode,
        "production_url": production_url,
        "production_status": None,
        "production_product_artifact_refs": [],
        "local_dev": None,
        "comparison": {},
        "diagnostic_artifacts": {
            "report": str(REPORT_DIR / "site-artifact-comparison.json"),
        },
        "recommendation": "If production and local dev differ, check the get-urirun-com deployment manifest and product artifact publication step.",
    }
    if mode not in {"production-site", "local-dev-site", "both"}:
        pytest.fail(f"unsupported GET_URIRUN_SITE_MODE={mode!r}")

    if mode in {"production-site", "both"}:
        status, text, error = fetch_text(production_url)
        report["production_status"] = status
        report["production_error"] = error
        report["production_product_artifact_refs"] = _production_artifact_refs(text, production_url)
        write_json_report("site-artifact-comparison.json", report)
        assert status and 200 <= status < 400

    if mode in {"local-dev-site", "both"}:
        repo = os.environ.get("GET_URIRUN_REPO_URL", "https://github.com/if-uri/get-urirun-com.git")
        ref = os.environ.get("GET_URIRUN_REF", "main")
        checkout = WORK / "get-urirun-com"
        if checkout.exists():
            shutil.rmtree(checkout)
        clone = subprocess.run(["git", "clone", "--depth", "1", "--branch", ref, repo, str(checkout)], cwd=ROOT, text=True, capture_output=True, timeout=120)
        if clone.returncode != 0:
            report["local_dev"] = {"repo": repo, "ref": ref, "clone_exit_code": clone.returncode, "stdout": clone.stdout, "stderr": clone.stderr}
            write_json_report("site-artifact-comparison.json", report)
            pytest.xfail("Local get-urirun-com checkout could not be cloned on this runner.")
        artifacts = _artifact_dir()
        target = checkout / "artifacts"
        target.mkdir(parents=True, exist_ok=True)
        for item in artifacts.glob("*"):
            if item.is_file():
                shutil.copy2(item, target / item.name)
        # The test harness cannot know every framework-specific dev server command
        # in get-urirun-com. It prepares the checkout plus product artifacts and
        # serves a deterministic local deployment simulation for pre-production checks.
        deploy_dir = _simulate_local_deployment(artifacts, [
            {"name": p.name, "path": str(p), "size": p.stat().st_size, "sha256": _sha256(p), "kind": p.suffix.lstrip("."), "platform": "local"}
            for p in artifacts.glob("*") if p.is_file() and p.name != "manifest.json"
        ])
        report["local_dev"] = {
            "repo": repo,
            "ref": ref,
            "checkout": str(checkout),
            "local_deployment_dir": str(deploy_dir),
            "note": "The harness prepared product artifacts for the local dev site checkout; actual project-specific dev server wiring is an integration point.",
        }
        report["comparison"] = {
            "production_refs_count": len(report["production_product_artifact_refs"]),
            "local_product_artifacts_count": len(list((REPORT_DIR / "local-deployment" / "artifacts").glob("*"))),
        }
        write_json_report("site-artifact-comparison.json", report)
