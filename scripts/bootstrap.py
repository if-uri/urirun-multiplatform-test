from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"
VENV = WORK / "venv"
VENV_META = VENV / ".urirun-test-venv.json"


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def venv_python() -> Path:
    return VENV / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")


def current_signature() -> dict[str, str]:
    return {
        "os_name": os.name,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": platform.python_version(),
        "venv_scheme": sysconfig.get_default_scheme(),
    }


def read_signature() -> dict[str, str] | None:
    if not VENV_META.exists():
        return None
    try:
        import json

        return json.loads(VENV_META.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_signature() -> None:
    import json

    VENV_META.write_text(json.dumps(current_signature(), indent=2), encoding="utf-8")


def ensure_compatible_venv() -> None:
    if not VENV.exists():
        return
    python = venv_python()
    previous = read_signature()
    if not python.exists() or previous != current_signature():
        print(f"Removing incompatible virtualenv: {VENV}", flush=True)
        shutil.rmtree(VENV)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    ensure_compatible_venv()
    if not VENV.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    python = venv_python()
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-e", str(ROOT)])
    write_signature()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
