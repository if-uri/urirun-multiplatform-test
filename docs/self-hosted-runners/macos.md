# macOS self-hosted runner

Use a real macOS host. macOS is not tested as a normal Docker container.

## System requirements

- macOS 13 or newer.
- Intel or Apple Silicon hardware.
- Network access to GitHub and to the configured `URIRUN_REPO_URL`.
- At least 2 CPU cores and 4 GB RAM.

## Required tools

- Homebrew.
- Python 3.10 or newer; Python 3.12 is recommended.
- Node.js 22 or newer.
- Git 2.44 or newer.
- Bash or zsh. The workflow uses `bash`.
- Optional: Docker Desktop if this host also runs Linux Docker checks.

## Apple Silicon vs Intel

- Homebrew is usually `/opt/homebrew` on Apple Silicon and `/usr/local` on Intel.
- Make sure the runner service has the same `PATH` you use interactively.
- Avoid mixing x86_64 Python under Rosetta with arm64 Homebrew packages unless you intentionally test that combination.

## Local pre-flight

```bash
brew install python@3.12 node git
git clone https://github.com/if-uri/urirun-multiplatform-test
cd urirun-multiplatform-test
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
python3 scripts/run_tests.py
```

If shell scripts are checked out without execute bits, run:

```bash
chmod +x scripts/*.py
```

The Python scripts are normally invoked with `python`, so execute bits are not required for CI.

## Runner labels

Example labels:

- `self-hosted`
- `macOS`
- `arm64` or `x64`
- `urirun`

Example workflow fragment:

```yaml
runs-on: [self-hosted, macOS, arm64, urirun]
shell: bash
```

## Common problems

- `python` points to Python 2 or is missing: install Python 3 and expose it as `python` or adjust the workflow.
- Homebrew tools are missing in runner service: add `/opt/homebrew/bin` or `/usr/local/bin` to the service environment.
- Permission errors in the runner work directory: make the runner user own the checkout and `.work/`.
- Node version is stale: update with Homebrew or install through `actions/setup-node`.
- Intel/Apple Silicon mismatch: confirm `python -c "import platform; print(platform.machine())"` and `brew --prefix`.
