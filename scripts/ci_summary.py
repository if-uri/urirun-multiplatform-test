from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"


def read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "invalid json", "path": str(path)}


def junit_summary(path: Path) -> dict[str, int] | None:
    if not path.exists():
        return None
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = list(root.findall("testsuite"))
    result = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in result:
            result[key] += int(float(suite.attrib.get(key, "0")))
    return result


def junit_cases(path: Path) -> dict[str, list[str]]:
    result = {"failed": [], "errors": [], "skipped": [], "xfailed": []}
    if not path.exists():
        return result
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    for case in root.iter("testcase"):
        name = "::".join(part for part in [case.attrib.get("classname"), case.attrib.get("name")] if part)
        if case.find("failure") is not None:
            result["failed"].append(name)
        if case.find("error") is not None:
            result["errors"].append(name)
        skipped = case.find("skipped")
        if skipped is not None:
            message = (skipped.attrib.get("message") or "").lower()
            skipped_type = (skipped.attrib.get("type") or "").lower()
            if "xfail" in message or "xfail" in skipped_type or "expected failure" in message:
                result["xfailed"].append(name)
            else:
                result["skipped"].append(name)
    return result


def bullet_json(name: str, payload: dict[str, Any] | list[Any] | None) -> list[str]:
    if payload is None:
        return [f"- `{name}`: not present"]
    if isinstance(payload, list):
        return [f"- `{name}`: {len(payload)} entries"]
    status = payload.get("status") or payload.get("deployment_mode") or payload.get("site_mode") or payload.get("profile") or "present"
    recommendation = payload.get("recommendation")
    line = f"- `{name}`: {status}"
    if recommendation:
        line += f" - {recommendation}"
    return [line]


def report_status(payload: dict[str, Any] | list[Any] | None) -> str:
    if payload is None:
        return "not present"
    if isinstance(payload, list):
        return f"{len(payload)} entries"
    if payload.get("external_blockers"):
        return "XFAIL / EXTERNAL BLOCKER"
    if payload.get("critical_console_errors") or payload.get("critical_failed_requests"):
        return "FAILED"
    if payload.get("comparison", {}).get("status"):
        return str(payload["comparison"]["status"])
    if payload.get("page_status") and not payload.get("exit_code"):
        return "download/hash only" if payload.get("installer_sha256") else "present"
    return str(payload.get("status") or payload.get("deployment_mode") or payload.get("site_mode") or payload.get("profile") or "present")


def build_summary() -> str:
    lines = ["# urirun multiplatform E2E summary", ""]
    summary = read_json(REPORT_DIR / "summary.json")
    validation = read_json(REPORT_DIR / "validation-report.json")
    junit = junit_summary(REPORT_DIR / "junit.xml")
    cases = junit_cases(REPORT_DIR / "junit.xml")
    if isinstance(summary, dict):
        profile = str(summary.get("profile", "unknown"))
        lines.extend([
            f"- Profile: `{profile}`",
            f"- urirun: `{summary.get('urirun', {}).get('stdout') or summary.get('urirun', {}).get('stderr') or 'unknown'}`",
            f"- JSON reports: {', '.join(summary.get('reports', [])) or 'none'}",
            f"- GitHub reports artifact: `reports-{profile}` or `diagnostic-reports-{profile}` depending on workflow job",
            f"- GitHub JUnit artifact: `junit-{profile}`",
        ])
    else:
        lines.append("- `summary.json`: not present")
    if junit:
        lines.append(f"- JUnit: {junit['tests']} tests, {junit['failures']} failures, {junit['errors']} errors, {junit['skipped']} skipped")
    else:
        lines.append("- `junit.xml`: not present")
    lines.append("")
    lines.append("## Test Outcomes")
    for label, values in [
        ("Failed", cases["failed"]),
        ("Errors", cases["errors"]),
        ("Skipped", cases["skipped"]),
        ("Xfail/expected", cases["xfailed"]),
    ]:
        if values:
            lines.append(f"- {label}: {len(values)}")
            for item in values[:20]:
                lines.append(f"  - `{item}`")
            if len(values) > 20:
                lines.append(f"  - ... and {len(values) - 20} more")
        else:
            lines.append(f"- {label}: 0")
    lines.append("")
    lines.append("## Validation")
    if isinstance(validation, dict):
        for row in validation.get("rows", []):
            lines.append(f"- {row.get('Area')}: **{row.get('Current status')}** - {row.get('Recommended action')}")
    else:
        lines.append("- validation report not present")
    lines.append("")
    lines.append("## Artifact Classes")
    if isinstance(summary, dict):
        product = summary.get("product_artifacts", {})
        diagnostic = summary.get("diagnostic_test_artifacts", {})
        product_files = product.get("files", []) if isinstance(product, dict) else []
        lines.append(f"- Product artifact files: {len(product_files)}")
        for item in product_files[:20]:
            lines.append(f"  - `{item}`")
        lines.append(f"- Diagnostic screenshots: {len(diagnostic.get('screenshots', [])) if isinstance(diagnostic, dict) else 0}")
        lines.append(f"- Diagnostic traces: {len(diagnostic.get('traces', [])) if isinstance(diagnostic, dict) else 0}")
        lines.append(f"- Diagnostic logs: {len(diagnostic.get('logs', [])) if isinstance(diagnostic, dict) else 0}")
    else:
        lines.append("- summary.json not present")
    deployment_report = read_json(REPORT_DIR / "deployment-bundle" / "deployment-report.json")
    if isinstance(deployment_report, dict):
        lines.append(f"- Deployment bundle: {deployment_report.get('status')} promotion_candidate={deployment_report.get('promotion_candidate')}")
    else:
        lines.append("- Deployment bundle: not present")
    lines.append("")
    lines.append("## E2E Surface Status")
    install_report = read_json(REPORT_DIR / "get-urirun-install.json")
    local_dev_report = read_json(REPORT_DIR / "local-dev-site.json")
    gui_report = read_json(REPORT_DIR / "gui-user-journey.json")
    site_report = read_json(REPORT_DIR / "site-artifact-comparison.json")
    lines.append(f"- Install flow: {report_status(install_report)}")
    lines.append(f"- Local dev site: {report_status(local_dev_report)}")
    lines.append(f"- GUI: {report_status(gui_report)}")
    lines.append(f"- Site comparison: {report_status(site_report)}")
    lines.append("")
    lines.append("## User Journey Reports")
    for name in [
        "product-artifacts-deployment.json",
        "site-artifact-comparison.json",
        "local-dev-site.json",
        "get-urirun-site.json",
        "get-urirun-install.json",
        "gui-user-journey.json",
    ]:
        lines.extend(bullet_json(name, read_json(REPORT_DIR / name)))
    lines.append("")
    lines.append("## Transport Reports")
    transport_reports = sorted(REPORT_DIR.glob("transport-*.json"))
    if not transport_reports:
        lines.append("- none present")
    for path in transport_reports:
        lines.extend(bullet_json(path.name, read_json(path)))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "ci-summary.md"
    path.write_text(build_summary(), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
