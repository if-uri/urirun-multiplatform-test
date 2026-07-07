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

from tests.deployment_bundle import (
    artifact_record,
    build_manifest,
    create_deployment_bundle,
    diff_manifests,
    discover_artifacts,
    validate_bundle,
    validate_manifest,
)
from tests.gui_utils import current_system, fetch_text, write_json_report
from tests.local_dev_site import clone_checkout, copy_bundle_into_checkout, detect_dev_server, start_detected_server


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
    for stale in artifact_dir.glob("urirun-*"):
        if stale.is_file():
            stale.unlink()
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


def _version_from_source(source: Path) -> str | None:
    version_file = source / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return None


def _deployment_bundle_dir() -> Path:
    return REPORT_DIR / "deployment-bundle"


def _production_artifact_refs(text: str, base_url: str) -> list[str]:
    refs = []
    for token in text.replace('"', " ").replace("'", " ").split():
        clean = token.strip("()[]{}<>,;")
        lower = clean.lower()
        if any(lower.endswith(suffix) for suffix in (".exe", ".whl", ".tar.gz", ".zip", ".ps1", ".sh", "manifest.json")):
            refs.append(urljoin(base_url, clean))
    return sorted(set(refs))


def _manifest_candidates(base_url: str, artifact_refs: list[str]) -> list[str]:
    candidates = [
        urljoin(base_url, "manifest.json"),
        urljoin(base_url, "deployment-bundle/manifest.json"),
        urljoin(base_url, "artifacts/manifest.json"),
    ]
    candidates.extend(ref for ref in artifact_refs if ref.lower().endswith("manifest.json"))
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _fetch_first_manifest(base_url: str, artifact_refs: list[str]) -> dict:
    attempts: list[dict] = []
    for candidate in _manifest_candidates(base_url, artifact_refs):
        status, body, error = fetch_text(candidate, timeout=10)
        attempt = {"url": candidate, "status": status, "error": error}
        if status and 200 <= status < 400 and body.strip():
            try:
                manifest = json.loads(body)
            except json.JSONDecodeError as exc:
                attempt["parse_error"] = str(exc)
            else:
                if isinstance(manifest, dict):
                    problems = validate_manifest(manifest)
                    return {"status": "found", "url": candidate, "manifest": manifest, "validation_problems": problems, "attempts": attempts + [attempt]}
                attempt["parse_error"] = "manifest root is not an object"
        attempts.append(attempt)
    return {
        "status": "not_found",
        "manifest": None,
        "validation_problems": ["production manifest contract is not discoverable"],
        "attempts": attempts,
    }


def _browser_smoke(url: str) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {"status": "not_run", "reason": f"Playwright unavailable: {exc}"}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            response = page.goto(url, wait_until="networkidle", timeout=30_000)
            title = page.title()
            body = page.locator("body").inner_text(timeout=10_000)[:1000]
            return {
                "status": "ok" if response and 200 <= response.status < 400 else "failed",
                "http_status": None if response is None else response.status,
                "title": title,
                "body_excerpt": body,
            }
        finally:
            browser.close()


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
        "deployment_bundle_dir": str(_deployment_bundle_dir()),
        "deployment_bundle_report": None,
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
    meta = _install_meta()
    records = discover_artifacts(artifact_dir)
    manifest = build_manifest(
        product="urirun",
        version=_version_from_source(source),
        repo_url=meta.get("repo_url") or os.environ.get("URIRUN_REPO_URL"),
        ref=meta.get("ref") or os.environ.get("URIRUN_REF"),
        revision=meta.get("revision"),
        artifacts=records,
    )
    bundle_report = create_deployment_bundle(
        artifact_dir=artifact_dir,
        bundle_dir=_deployment_bundle_dir(),
        manifest=manifest,
        artifacts=records,
    )
    report["deployment_bundle_report"] = bundle_report
    write_json_report("product-artifacts-deployment.json", report)
    assert bundle_report["promotion_candidate"], bundle_report


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
        "production_manifest": None,
        "local_dev": None,
        "comparison": {},
        "diff_report": {},
        "installer_links": [],
        "artifact_endpoint_status": {},
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
        report["installer_links"] = [ref for ref in report["production_product_artifact_refs"] if ref.lower().endswith((".ps1", ".sh"))]
        report["production_manifest"] = _fetch_first_manifest(production_url, report["production_product_artifact_refs"])
        for ref in report["production_product_artifact_refs"][:20]:
            endpoint_status, _, endpoint_error = fetch_text(ref, timeout=10)
            report["artifact_endpoint_status"][ref] = {"status": endpoint_status, "error": endpoint_error}
        report["comparison"] = {
            "status": "PARTIAL" if not report["production_manifest"].get("manifest") else "DONE",
            "partial_reason": None if report["production_manifest"].get("manifest") else "production manifest contract is not discoverable; comparison uses artifact refs and endpoint checks only",
            "production_refs_count": len(report["production_product_artifact_refs"]),
            "installer_links_count": len(report["installer_links"]),
            "checked_endpoint_count": len(report["artifact_endpoint_status"]),
        }
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
        bundle_dir = _deployment_bundle_dir()
        copied = copy_bundle_into_checkout(bundle_dir, checkout)
        plan = detect_dev_server(checkout)
        local_dev_report = {
            "repo": repo,
            "ref": ref,
            "checkout": str(checkout),
            "copied": copied,
            "dev_server_plan": plan.as_dict(),
            "fetch": None,
            "recommendation": "Add a stable get-urirun-com dev/start command or static index.html contract if status is integration_required.",
        }
        process = None
        if plan.status == "detected":
            try:
                process, local_url = start_detected_server(plan)
                status, text, error = fetch_text(local_url, timeout=30)
                local_dev_report["fetch"] = {"url": local_url, "status": status, "error": error, "body_excerpt": text[:1000]}
                local_dev_report["browser_smoke"] = _browser_smoke(local_url)
            finally:
                if process is not None:
                    process.terminate()
        write_json_report("local-dev-site.json", local_dev_report)
        if plan.status != "detected":
            report["local_dev"] = local_dev_report
            write_json_report("site-artifact-comparison.json", report)
            pytest.xfail(f"Local get-urirun-com dev server integration required: {plan.reason}")

        artifact_dir = _artifact_dir()
        deploy_dir = _simulate_local_deployment(artifact_dir, [
            artifact_record(p).as_manifest_item()
            for p in artifact_dir.glob("*") if p.is_file() and p.name != "manifest.json"
        ])
        report["local_dev"] = {
            "repo": repo,
            "ref": ref,
            "checkout": str(checkout),
            "local_deployment_dir": str(deploy_dir),
            "dev_server_plan": plan.as_dict(),
            "fetch": local_dev_report["fetch"],
        }
        bundle_validation = validate_bundle(bundle_dir)
        local_manifest_path = bundle_dir / "manifest.json"
        if local_manifest_path.exists():
            local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
            production_manifest = (report.get("production_manifest") or {}).get("manifest") or {"artifacts": [], "version": None, "ref": None, "revision": None}
            report["diff_report"] = diff_manifests(local_manifest, production_manifest)
        report["comparison"] = {
            "status": "PARTIAL" if not ((report.get("production_manifest") or {}).get("manifest")) else "DONE",
            "partial_reason": None if ((report.get("production_manifest") or {}).get("manifest")) else "production manifest contract is not discoverable; comparison uses artifact refs and endpoint checks only",
            "production_refs_count": len(report["production_product_artifact_refs"]),
            "local_product_artifacts_count": len(list((REPORT_DIR / "local-deployment" / "artifacts").glob("*"))),
            "deployment_bundle": bundle_validation,
        }
        write_json_report("site-artifact-comparison.json", report)
