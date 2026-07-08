from __future__ import annotations

import json
import re
import time
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
VALID_STATUSES = {"DONE", "PARTIAL", "DOCUMENTED ONLY", "EXPERIMENTAL", "XFAIL", "TODO", "EXTERNAL BLOCKER", "NOT VERIFIED"}
KEY_FILES = [
    "README.md",
    "docs/TODO.md",
    "docs/IMPLEMENTED.md",
    "docs/multiplatform-e2e-design.md",
    "docs/gui-test-contract.md",
    "docs/ci-verification.md",
    "docs/main-repo-trigger-workflow.md",
    "docs/docker-compose-matrix.md",
    "docs/external-contracts/main-urirun.md",
    "docs/external-contracts/get-urirun-com.md",
    "docs/external-contracts/production-promotion.md",
    ".github/workflows/multiplatform.yml",
    "pyproject.toml",
    "scripts/run_tests.py",
    "scripts/collect_report.py",
    "scripts/ci_summary.py",
    "scripts/validate_repo.py",
    "tests/gui_utils.py",
    "tests/deployment_bundle.py",
    "tests/test_deployment_bundle_helpers.py",
    "tests/test_product_artifacts_deployment.py",
    "tests/test_get_urirun_site.py",
    "tests/test_get_urirun_install_flow.py",
    "tests/test_gui_user_journey.py",
    "tests/test_gui_error_policy.py",
    "tests/test_transports.py",
    "docker/linux/Dockerfile",
]
REQUIRED_PROFILES = [
    "linux-docker",
    "windows-runner",
    "macos-runner",
    "linux-installer-gui",
    "windows-installer-gui",
    "macos-installer-gui",
]
REQUIRED_REPORT_NAMES = [
    "summary.json",
    "junit.xml",
    "ci-summary.md",
    "validation-report.json",
    "gui-user-journey.json",
    "product-artifacts-deployment.json",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def pytest_markers() -> set[str]:
    pyproject = tomllib.loads(read_text(ROOT / "pyproject.toml"))
    markers = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])
    return {item.split(":", 1)[0].strip() for item in markers}


def used_markers() -> set[str]:
    markers: set[str] = set()
    for path in (ROOT / "tests").glob("test_*.py"):
        text = read_text(path)
        markers.update(re.findall(r"pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)", text))
    return {marker for marker in markers if marker not in {"skipif", "parametrize", "xfail"}}


def status_for(area: str, evidence_exists: bool, external: bool = False, experimental: bool = False, partial: bool = False) -> str:
    if external:
        return "EXTERNAL BLOCKER"
    if not evidence_exists:
        return "TODO"
    if experimental:
        return "EXPERIMENTAL"
    if partial:
        return "PARTIAL"
    return "DONE"


def missing_substrings(text: str, required: list[str]) -> list[str]:
    return [item for item in required if item not in text]


def workflow_text() -> str:
    return read_text(ROOT / ".github" / "workflows" / "multiplatform.yml")


def workflow_dispatch_missing(text: str) -> list[str]:
    required = [
        "workflow_dispatch:",
        "repository_dispatch:",
        "urirun_repo_url",
        "urirun_ref",
        "get_urirun_site_mode",
        "allow_remote_install",
        "github.event.client_payload.urirun_repo_url",
        "github.event.client_payload.urirun_ref",
        "github.event.client_payload.sha",
        "URIRUN_REPO_URL:",
        "URIRUN_REF:",
    ]
    return missing_substrings(text, required)


def workflow_shell_missing(text: str) -> list[str]:
    expectations = [
        "matrix.profile == 'windows-runner'\n        shell: pwsh",
        "matrix.profile == 'macos-runner'\n        shell: bash",
        "matrix.profile == 'windows-installer-gui'\n        shell: pwsh",
        "matrix.profile == 'macos-installer-gui'\n        shell: bash",
    ]
    return missing_substrings(text, expectations)


def build_rows() -> list[dict[str, Any]]:
    docs = {name: read_text(ROOT / name) for name in ["README.md", "docs/TODO.md", "docs/IMPLEMENTED.md", "docs/multiplatform-e2e-design.md"]}
    marker_missing = sorted(used_markers() - pytest_markers())
    key_missing = [name for name in KEY_FILES if not (ROOT / name).exists()]
    workflow = workflow_text()
    profile_missing = missing_substrings(workflow, REQUIRED_PROFILES)
    dispatch_missing = workflow_dispatch_missing(workflow)
    shell_missing = workflow_shell_missing(workflow)
    report_missing = missing_substrings(
        read_text(ROOT / "scripts" / "collect_report.py")
        + read_text(ROOT / "scripts" / "ci_summary.py")
        + read_text(ROOT / "scripts" / "run_tests.py"),
        REQUIRED_REPORT_NAMES,
    )
    gui_missing = missing_substrings(
        read_text(ROOT / "tests" / "gui_utils.py") + read_text(ROOT / "tests" / "test_gui_user_journey.py"),
        [
            "URIRUN_GUI_ALLOWED_CONSOLE_ERROR_PATTERNS",
            "URIRUN_GUI_ALLOWED_NETWORK_ERROR_PATTERNS",
            "URIRUN_PLAYWRIGHT_TRACE_MODE",
            "URIRUN_PLAYWRIGHT_VIDEO_MODE",
            "data-testid",
            "aria-label",
        ],
    )
    bundle_missing = missing_substrings(
        read_text(ROOT / "tests" / "deployment_bundle.py") + read_text(ROOT / "tests" / "test_deployment_bundle_helpers.py"),
        [
            "checksums/SHA256SUMS",
            "deployment-report.json",
            "missing checksum target",
            "checksum mismatch",
            "orphaned artifact",
            "future_artifacts",
        ],
    )
    return [
        {
            "Area": "Key repository files",
            "Expected": "All documented harness files exist",
            "Current status": "DONE" if not key_missing else "PARTIAL",
            "Evidence": ", ".join(KEY_FILES),
            "Tests run": "scripts/validate_repo.py",
            "Tests not run / reason": "CI matrix not inferred locally",
            "Risk": "Missing files make docs or CI stale" if key_missing else "Low",
            "Recommended action": "Restore missing files: " + ", ".join(key_missing) if key_missing else "Keep validation in CI",
        },
        {
            "Area": "Documentation consistency",
            "Expected": "README, TODO, IMPLEMENTED and design docs use compatible status language",
            "Current status": "PARTIAL" if any("local-deployment" in text for text in docs.values()) else "DONE",
            "Evidence": "docs/TODO.md status definitions; docs/VALIDATION_REPORT.md generated table",
            "Tests run": "scripts/validate_repo.py",
            "Tests not run / reason": "Human semantic review still required for nuanced claims",
            "Risk": "Docs can overstate deployment readiness",
            "Recommended action": "Keep PARTIAL/EXTERNAL BLOCKER claims for platform installers and production deployment",
        },
        {
            "Area": "Pytest marker registry",
            "Expected": "All pytest.mark names used by tests are declared in pyproject.toml",
            "Current status": "DONE" if not marker_missing else "PARTIAL",
            "Evidence": f"declared={sorted(pytest_markers())}; missing={marker_missing}",
            "Tests run": "scripts/validate_repo.py",
            "Tests not run / reason": "N/A",
            "Risk": "Strict marker failures" if marker_missing else "Low",
            "Recommended action": "Add missing markers to pyproject.toml" if marker_missing else "No action",
        },
        {
            "Area": "Workflow profiles and dispatch inputs",
            "Expected": "workflow_dispatch, repository_dispatch, all six profiles, payload mapping and OS-specific shells are wired",
            "Current status": "DONE" if not (profile_missing or dispatch_missing or shell_missing) else "PARTIAL",
            "Evidence": ".github/workflows/multiplatform.yml; docs/main-repo-trigger-workflow.md",
            "Tests run": "scripts/validate_repo.py",
            "Tests not run / reason": "Structural validation only; does not prove GitHub-hosted runner success",
            "Risk": "Main repo cannot trigger exact-ref E2E runs" if dispatch_missing else "Workflow can still fail only at runtime",
            "Recommended action": (
                "Fix missing workflow wiring: "
                + ", ".join(profile_missing + dispatch_missing + shell_missing)
                if (profile_missing or dispatch_missing or shell_missing)
                else "Keep repository_dispatch trigger and profile matrix under validation"
            ),
        },
        {
            "Area": "Required report generation",
            "Expected": "summary, JUnit, CI markdown, validation, GUI and product-artifact reports are generated or documented",
            "Current status": "DONE" if not report_missing else "PARTIAL",
            "Evidence": "scripts/run_tests.py; scripts/collect_report.py; scripts/ci_summary.py",
            "Tests run": "scripts/validate_repo.py; tests/test_reporting_scripts.py",
            "Tests not run / reason": "Some reports are emitted only by user-journey tests",
            "Risk": "CI failures become hard to diagnose" if report_missing else "Low",
            "Recommended action": "Add missing report wiring: " + ", ".join(report_missing) if report_missing else "No action",
        },
        {
            "Area": "Deployment bundle",
            "Expected": "reports/deployment-bundle has manifest, artifacts, checksums, site and deployment-report",
            "Current status": "DONE" if not bundle_missing else "PARTIAL",
            "Evidence": "tests/deployment_bundle.py; tests/test_deployment_bundle_helpers.py",
            "Tests run": "helper unit tests; user journey test when active",
            "Tests not run / reason": "Production promotion is intentionally dry-run only",
            "Risk": "Platform installers remain external",
            "Recommended action": "Use bundle as promotion candidate input for trusted deployment job" if not bundle_missing else "Fix missing bundle contract checks: " + ", ".join(bundle_missing),
        },
        {
            "Area": "Platform artifacts",
            "Expected": "Wheel/sdist are real; exe/deb/rpm/pkg/app are future external artifacts",
            "Current status": "EXTERNAL BLOCKER",
            "Evidence": "manifest future_artifacts entries use EXTERNAL BLOCKER",
            "Tests run": "tests/test_deployment_bundle_helpers.py",
            "Tests not run / reason": "Main urirun platform artifact pipelines are outside this repo",
            "Risk": "End-to-end native installer validation is incomplete",
            "Recommended action": "Add platform build pipelines in if-uri/urirun, then consume artifacts here",
        },
        {
            "Area": "Local get-urirun-com dev server",
            "Expected": "Detect Node/static stack or xfail with integration_required report",
            "Current status": "PARTIAL",
            "Evidence": "tests/local_dev_site.py; reports/local-dev-site.json",
            "Tests run": "tests/test_local_dev_site.py",
            "Tests not run / reason": "Real get-urirun-com clone requires network and repo contract",
            "Risk": "Local pre-production site may not match production",
            "Recommended action": "Define stable dev/start command in get-urirun-com",
        },
        {
            "Area": "GUI test contract and error policy",
            "Expected": "Stable selector preference, strict default allowlist, trace/video retention controls",
            "Current status": "EXPERIMENTAL" if not gui_missing else "PARTIAL",
            "Evidence": "docs/gui-test-contract.md; tests/gui_utils.py; tests/test_gui_error_policy.py",
            "Tests run": "tests/test_gui_error_policy.py",
            "Tests not run / reason": "Dashboard UI behavior depends on tested urirun ref",
            "Risk": "Dashboard can emit legitimate xfail-worthy browser errors",
            "Recommended action": "Add data-testid attributes and reduce dashboard console/network errors in main urirun" if not gui_missing else "Fix missing GUI controls: " + ", ".join(gui_missing),
        },
        {
            "Area": "CI reporting",
            "Expected": "reports/ci-summary.md is generated and appended to GITHUB_STEP_SUMMARY",
            "Current status": "DONE" if (ROOT / "scripts" / "ci_summary.py").exists() else "TODO",
            "Evidence": "scripts/ci_summary.py; .github/workflows/multiplatform.yml",
            "Tests run": "scripts/ci_summary.py unit-level execution",
            "Tests not run / reason": "GitHub summary rendering only occurs in Actions",
            "Risk": "Low",
            "Recommended action": "Inspect uploaded reports for failed CI jobs",
        },
        {
            "Area": "CI verification",
            "Expected": "All six GitHub Actions profiles have recorded run evidence",
            "Current status": "NOT VERIFIED",
            "Evidence": ".github/workflows/multiplatform.yml; docs/ci-verification.md",
            "Tests run": "Not run by local validation",
            "Tests not run / reason": "Requires GitHub Actions execution outside this local repository workspace",
            "Risk": "Workflow may be defined but not actually passing on GitHub-hosted runners",
            "Recommended action": "Run workflow_dispatch and record run URLs plus artifacts in VALIDATION_REPORT.md",
        },
        {
            "Area": "External contracts",
            "Expected": "External blockers are documented as contracts rather than claimed done",
            "Current status": "DOCUMENTED ONLY",
            "Evidence": "docs/external-contracts/main-urirun.md; docs/external-contracts/get-urirun-com.md; docs/external-contracts/production-promotion.md",
            "Tests run": "Documentation presence check",
            "Tests not run / reason": "Requires changes in external repositories or trusted CI/CD",
            "Risk": "External owners must implement the contracts before statuses can advance",
            "Recommended action": "Use these contracts as acceptance criteria for external repo work",
        },
    ]


def write_validation_report(rows: list[dict[str, Any]]) -> None:
    report_path = ROOT / "docs" / "VALIDATION_REPORT.md"
    header = "# VALIDATION REPORT\n\nGenerated by `python scripts/validate_repo.py`.\n\n"
    columns = ["Area", "Expected", "Current status", "Evidence", "Tests run", "Tests not run / reason", "Risk", "Recommended action"]
    table = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        table.append("| " + " | ".join(str(row[column]).replace("\n", " ") for column in columns) + " |")
    report_path.write_text(header + "\n".join(table) + "\n", encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "valid_statuses": sorted(VALID_STATUSES),
        "rows": rows,
    }
    write_validation_report(rows)
    (REPORT_DIR / "validation-report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
