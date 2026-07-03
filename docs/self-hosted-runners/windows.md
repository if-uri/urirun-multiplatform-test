# Windows self-hosted runner

Use a real Windows host or VM. Do not substitute this profile with a Linux Docker container.

## System requirements

- Windows Server 2022 or Windows 11.
- Administrator access for installing tools and enabling long paths.
- Network access to GitHub and to the configured `URIRUN_REPO_URL`.
- At least 2 CPU cores and 4 GB RAM.

## Required tools

- PowerShell 7 (`pwsh`) recommended; Windows PowerShell 5.1 is acceptable for local debugging.
- `cmd.exe` from Windows for shell compatibility tests.
- Git for Windows 2.44 or newer.
- Python 3.10 or newer. Python 3.12 is recommended to match GitHub-hosted runners.
- Node.js 22 or newer.
- Optional: Docker Desktop only if you intentionally run Linux Docker tests from this Windows host.

## Windows setup notes

- Enable long paths:
  `New-ItemProperty -Path HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem -Name LongPathsEnabled -Value 1 -PropertyType DWord -Force`
- Prefer UTF-8:
  set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` in the runner service environment.
- Ensure `python`, `py`, `git`, `node`, `npm`, `pwsh`, and `cmd.exe` are on `PATH`.
- The Python launcher `py -3.12` is useful for diagnostics, but CI commands should call `python`.
- Git Bash is not the same as native PowerShell. The workflow uses `pwsh` for Windows because it matches Windows paths and process behavior. Git Bash may translate paths and can hide quoting bugs.

## Local pre-flight

```powershell
git clone https://github.com/if-uri/urirun-multiplatform-test
cd urirun-multiplatform-test
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
python scripts\run_tests.py
```

## Runner labels

Example labels:

- `self-hosted`
- `windows`
- `x64`
- `urirun`

Example workflow fragment:

```yaml
runs-on: [self-hosted, windows, x64, urirun]
shell: pwsh
```

## Common problems

- `python` resolves to Microsoft Store: install Python from python.org or disable Store aliases.
- `urirun` is not found from `cmd.exe`: check `PATH`; the test harness prepends `.work/venv/Scripts`, but the runner service must inherit a sane base path.
- Unicode output is garbled: set `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, and use PowerShell 7.
- Long paths fail during pip install: enable long paths and avoid deeply nested runner work directories.
- Git Bash passes locally but CI fails: reproduce with `pwsh`, because Windows CI intentionally uses native PowerShell.
