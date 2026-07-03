from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".work" / "venv"


def bin_path(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return VENV / ("Scripts" if os.name == "nt" else "bin") / f"{name}{suffix}"


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    run([sys.executable, str(ROOT / "scripts" / "bootstrap.py")])
    run([sys.executable, str(ROOT / "scripts" / "install_urirun.py")])
    env = os.environ.copy()
    env["URIRUN_TEST_VENV"] = str(VENV)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    pytest_args = argv or ["-q"]
    run([str(bin_path("python")), "-m", "pytest", *pytest_args], env=env)
    run([str(bin_path("python")), str(ROOT / "scripts" / "collect_report.py")], env=env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
