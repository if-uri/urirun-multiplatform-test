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


def build_summary() -> str:
    lines = ["# urirun multiplatform E2E summary", ""]
    summary = read_json(REPORT_DIR / "summary.json")
    validation = read_json(REPORT_DIR / "validation-report.json")
    junit = junit_summary(REPORT_DIR / "junit.xml")
    if isinstance(summary, dict):
        lines.extend([
            f"- Profile: `{summary.get('profile', 'unknown')}`",
            f"- urirun: `{summary.get('urirun', {}).get('stdout') or summary.get('urirun', {}).get('stderr') or 'unknown'}`",
            f"- JSON reports: {', '.join(summary.get('reports', [])) or 'none'}",
        ])
    else:
        lines.append("- `summary.json`: not present")
    if junit:
        lines.append(f"- JUnit: {junit['tests']} tests, {junit['failures']} failures, {junit['errors']} errors, {junit['skipped']} skipped")
    else:
        lines.append("- `junit.xml`: not present")
    lines.append("")
    lines.append("## Validation")
    if isinstance(validation, dict):
        for row in validation.get("rows", []):
            lines.append(f"- {row.get('Area')}: **{row.get('Current status')}** - {row.get('Recommended action')}")
    else:
        lines.append("- validation report not present")
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
