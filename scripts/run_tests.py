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


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[None]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env, check=True)


def should_install_gui_deps(argv: list[str]) -> bool:
    profile = os.environ.get("URIRUN_TEST_PROFILE", "")
    if "installer-gui" in profile or profile == "user-journey":
        return True
    gui_tests = {
        "test_get_urirun_site.py",
        "test_get_urirun_install_flow.py",
        "test_gui_user_journey.py",
    }
    return any(any(name in arg for name in gui_tests) for arg in argv)


def install_gui_deps(env: dict[str, str]) -> None:
    run([str(bin_path("python")), "-m", "pip", "install", "-e", f"{ROOT}[gui]"], env=env)
    install_args = ["install", "chromium"]
    if sys.platform.startswith("linux"):
        install_args = ["install", "--with-deps", "chromium"]
    run([str(bin_path("python")), "-m", "playwright", *install_args], env=env)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    run([sys.executable, str(ROOT / "scripts" / "bootstrap.py")])
    run([sys.executable, str(ROOT / "scripts" / "install_urirun.py")])
    env = os.environ.copy()
    env["URIRUN_TEST_VENV"] = str(VENV)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if should_install_gui_deps(argv):
        env["URIRUN_USER_JOURNEY_ACTIVE"] = "1"
        install_gui_deps(env)
    pytest_args = argv or ["-q"]
    if not any(arg == "--junitxml" or arg.startswith("--junitxml=") for arg in pytest_args):
        pytest_args = [*pytest_args, "--junitxml", str(ROOT / "reports" / "junit.xml")]
    test_rc = 0
    try:
        run([str(bin_path("python")), "-m", "pytest", *pytest_args], env=env)
    except subprocess.CalledProcessError as exc:
        test_rc = exc.returncode
    finally:
        try:
            run([str(bin_path("python")), str(ROOT / "scripts" / "collect_report.py")], env=env)
        except subprocess.CalledProcessError as exc:
            if test_rc == 0:
                test_rc = exc.returncode
    return test_rc


if __name__ == "__main__":
    raise SystemExit(main())
