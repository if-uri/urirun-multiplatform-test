# urirun-multiplatform-test

[![urirun multiplatform e2e](https://github.com/if-uri/urirun-multiplatform-test/actions/workflows/multiplatform.yml/badge.svg)](https://github.com/if-uri/urirun-multiplatform-test/actions/workflows/multiplatform.yml)

Standalone black-box smoke and E2E harness for `urirun`. The repository fetches a selected `urirun` version, installs it into a fresh virtualenv, runs real CLI and transport scenarios, and writes diagnostics to `reports/`.

## Architecture

Linux is tested through Docker because Linux containers are a normal, repeatable test environment.

Windows and macOS are not treated as ordinary Docker containers. They are tested on GitHub Actions runners (`windows-latest`, `macos-latest`) or equivalent self-hosted runners. That split is intentional: Windows/macOS containers are not a technically or legally equivalent substitute for full OS runners for this E2E surface.

## Profiles

- `linux-docker` - builds `docker/linux/Dockerfile` and runs the full suite in a Linux container.
- `windows-runner` - runs the suite directly on Windows through `pwsh`.
- `macos-runner` - runs the suite directly on macOS through `bash`.

## Environment

- `URIRUN_REPO_URL` - repository URL for the tested `urirun`; default `https://github.com/if-uri/urirun.git`.
- `URIRUN_REF` - branch, tag, or commit to test; default `main`.
- `URIRUN_SOURCE_DIR` - optional local checkout of `urirun`; useful for development, still performs a real package install.
- `URIRUN_TEST_PROFILE` - profile name, usually set by CI.
- `URIRUN_TEST_VENV` - virtualenv path used by tests; normally set by `scripts/run_tests.py`.

## Local Run

From GitHub:

```bash
python scripts/run_tests.py
```

From a local `urirun` checkout:

```bash
URIRUN_SOURCE_DIR=/path/to/urirun python scripts/run_tests.py
```

Windows PowerShell:

```powershell
$env:URIRUN_SOURCE_DIR="C:\Users\Praca\fork\if-uri\urirun"
python scripts\run_tests.py
```

After a fresh checkout, no manual `.work/` setup is required. `scripts/run_tests.py` creates `.work/venv`, installs the test harness, fetches or uses `urirun`, installs it, runs pytest, writes `reports/summary.json`, and writes `reports/junit.xml`.

## Docker Linux

```bash
docker build -t urirun-linux-test -f docker/linux/Dockerfile .
docker run --rm urirun-linux-test
```

To keep reports outside the container:

```bash
docker run --rm -v "$PWD/reports:/workspace/reports" urirun-linux-test
```

## GitHub Actions

Workflow: `.github/workflows/multiplatform.yml`.

The matrix runs:

- `linux-docker / ubuntu-latest`
- `windows-runner / windows-latest`
- `macos-runner / macos-latest`

The workflow checks out this test repository, installs Python and Node, fetches and installs `urirun`, runs the full test suite, uploads `reports/`, uploads `reports/junit.xml`, and writes a readable GitHub Actions summary.

## Self-Hosted Runners

Self-hosted runner setup guides:

- [Windows self-hosted runner](docs/self-hosted-runners/windows.md)
- [macOS self-hosted runner](docs/self-hosted-runners/macos.md)
- [Linux self-hosted runner](docs/self-hosted-runners/linux.md)

Use these when replacing GitHub-hosted runners with company-managed Windows, macOS, or Linux hosts.

## Reports

Generated reports live in `reports/`:

- `summary.json` - OS, Python, Node, `urirun`, install metadata, and artifact list.
- `junit.xml` - pytest JUnit report for CI systems.
- `install-warning.json` - recorded when `urirun` package dependency resolution needs fallback handling.
- `transport-*.json` - structured transport failure reports with server/client logs.
- `*.stdout.log` and `*.stderr.log` - server process logs for transport tests.

Transport failure reports include transport, host, port, server command, client command, server stdout/stderr, client stdout/stderr, exit code, OS, Python version, `urirun` version, and a repair recommendation.

## Completed / Covered In This Repository

- Linux Docker profile.
- Windows GitHub Actions runner.
- macOS GitHub Actions runner.
- Installation smoke test.
- CLI tests.
- Registry tests.
- Connector smoke tests.
- Permission and allow-list tests.
- Path and shell tests.
- Structured JSON reports.
- JUnit report.
- Stable HTTP transport smoke test.
- Experimental MCP stdio transport smoke test.
- Experimental gRPC transport smoke test when optional `grpcio` is available.
- Self-hosted runner documentation for Windows, macOS, and Linux.

## Current Tests

Implemented coverage includes:

- `urirun --version`
- `urirun doctor --json`
- `urirun version --no-check`
- main command help
- `validate`
- `compile`
- `discover`
- `tree --format json`
- `gen openapi`
- `agent space`
- `errors bindings`
- `add-command`
- `node init/config`
- `host init/add-node/config`
- `urirun run`
- invalid command and invalid URI behavior
- connector doctor and safe connector install dry-run coverage
- deny-by-default and wrong allow-list behavior
- native paths, paths with spaces, and output paths with spaces
- bash, PowerShell, and Windows `cmd.exe` shell coverage where available
- HTTP node `/health` and `/run`
- MCP `tools/call` over stdio
- gRPC server/client roundtrip when optional gRPC dependencies are installed
- error reporting for an intentionally failing route

## Stability Markers

- `stable` - expected to pass across Linux Docker, Windows runner, and macOS runner.
- `experimental` - real coverage for a surface that may still depend on optional packages or evolving behavior.
- `expected_failure` - known behavior gap, normally paired with `xfail`.

## Remaining Work In This Repository

- Optional richer transport logs, for example timing and request/response excerpts for successful HTTP/MCP/gRPC runs.
- Optional Docker Compose matrix coverage that mirrors more of `urirun/examples/matrix` without pulling unrelated language SDK runtimes into every CI run.
- Optional self-hosted runner workflow variants that use organization-specific runner labels.

## External Blockers In Main `urirun`

These items depend on changes in the main `urirun` repository and should not be hidden or pretended fixed in this test repository:

- Remove the installation fallback after `urirun` publishes or vendors all dependencies declared by `adapters/python/pyproject.toml` (`urirun-contract`, `urirun-connector-router`, `urirun-flow`, and version constraints).
- Remove the `xfail` from `connectors show planfile` after the main `urirun` CLI handler supports the command exposed by its parser.
- Promote gRPC transport coverage from experimental to stable only after the tested `urirun` install path consistently includes the required optional `grpcio` dependency on all target platforms.
