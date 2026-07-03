from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
VENV = Path(os.environ.get("URIRUN_TEST_VENV", ROOT / ".work" / "venv"))
INSTALL_META = ROOT / ".work" / "install-meta.json"


def bin_path(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return VENV / ("Scripts" if os.name == "nt" else "bin") / f"{name}{suffix}"


def capture(command: list[str]) -> dict[str, object]:
    try:
        cp = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=30)
        return {"command": command, "exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    except Exception as exc:
        return {"command": command, "exit_code": None, "stdout": "", "stderr": repr(exc)}


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    install_meta = {}
    if INSTALL_META.exists():
        try:
            install_meta = json.loads(INSTALL_META.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            install_meta = {"error": "install metadata is not valid JSON"}
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profile": os.environ.get("URIRUN_TEST_PROFILE", "local"),
        "system": {
            "os": platform.platform(),
            "python": sys.version,
        },
        "node": capture(["node", "--version"]),
        "urirun": capture([str(bin_path("urirun")), "--version"]),
        "install": install_meta,
        "reports": sorted(p.name for p in REPORT_DIR.glob("*.json") if p.name != "summary.json"),
        "product_artifacts": {
            "directory": str(REPORT_DIR / "product-artifacts"),
            "local_deployment_directory": str(REPORT_DIR / "local-deployment" / "artifacts"),
            "files": sorted(
                str(p.relative_to(REPORT_DIR))
                for folder in [REPORT_DIR / "product-artifacts", REPORT_DIR / "local-deployment" / "artifacts", REPORT_DIR / "installer"]
                if folder.exists()
                for p in folder.glob("*")
                if p.is_file()
            ),
        },
        "diagnostic_test_artifacts": {
            "screenshots": sorted(str(p.relative_to(REPORT_DIR)) for p in (REPORT_DIR / "screenshots").glob("*") if p.is_file()) if (REPORT_DIR / "screenshots").exists() else [],
            "traces": sorted(str(p.relative_to(REPORT_DIR)) for p in (REPORT_DIR / "traces").glob("*") if p.is_file()) if (REPORT_DIR / "traces").exists() else [],
            "logs": sorted(str(p.relative_to(REPORT_DIR)) for p in REPORT_DIR.glob("*.log")),
        },
    }
    path = REPORT_DIR / "summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
