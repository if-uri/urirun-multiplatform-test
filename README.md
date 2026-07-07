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
- `installer-gui-e2e` / `user-journey` - builds product artifacts, checks `get.urirun.com`, runs controlled installer flow, launches the dashboard GUI, and clicks through it with Playwright.
- `desktop-kvm-e2e` - boots a `docker/desktop-pc` virtual desktop (Xvfb + openbox + x11vnc + noVNC) with a real `urirun node serve --execute` and `urirun-connector-kvm` inside, then automates a user task purely through mesh `kvm://` / `app://` URIs: launch a terminal, type, screenshot, OCR-verify. Watch it live at `http://127.0.0.1:16080/vnc.html`. Enable with `URIRUN_TEST_PROFILE=desktop-kvm-e2e` or `URIRUN_DESKTOP_KVM_E2E=1` (needs Docker); evidence lands in `reports/screenshots/desktop-kvm/` and `reports/desktop-kvm-doctor.json`.

## Environment

- `URIRUN_REPO_URL` - repository URL for the tested `urirun`; default `https://github.com/if-uri/urirun.git`.
- `URIRUN_REF` - branch, tag, or commit to test; default `main`.
- `URIRUN_SOURCE_DIR` - optional local checkout of `urirun`; useful for development, still performs a real package install.
- `URIRUN_TEST_PROFILE` - profile name, usually set by CI.
- `URIRUN_TEST_VENV` - virtualenv path used by tests; normally set by `scripts/run_tests.py`.
- `GET_URIRUN_PRODUCTION_URL` - production install site; default `https://get.urirun.com/`.
- `GET_URIRUN_REPO_URL` - local-dev install site repo; default `https://github.com/if-uri/get-urirun-com.git`.
- `GET_URIRUN_REF` - ref for the local-dev install site; default `main`.
- `GET_URIRUN_SITE_MODE` - `production-site`, `local-dev-site`, or `both`; default `production-site`.
- `GET_URIRUN_INSTALL_MODE` - `site`, `local-repo`, or `skip`; default `site`.
- `GET_URIRUN_ALLOW_REMOTE_INSTALL` - `0` by default; set `1` only in trusted CI to execute remote installer scripts.
- `URIRUN_ARTIFACTS_DIR` - optional directory for product artifacts; default `reports/product-artifacts`.
- `URIRUN_DEPLOYMENT_MODE` - `local-simulated` by default for safe CI; `production` is reported as an external CI/CD requirement.
- `URIRUN_GUI_E2E` - set `0` to skip GUI browser tests.
- `URIRUN_GUI_ALLOWED_CONSOLE_ERROR_PATTERNS` - optional regex allowlist for accepted browser console errors; default is empty and restrictive.
- `URIRUN_GUI_ALLOWED_NETWORK_ERROR_PATTERNS` - optional regex allowlist for accepted failed browser requests; default is empty and restrictive.
- `URIRUN_PLAYWRIGHT_TRACE_MODE` - `always`, `on-failure`, or `off`; default `on-failure`.
- `URIRUN_PLAYWRIGHT_VIDEO_MODE` - `always`, `on-failure`, or `off`; default `off`.

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

Optional Linux Compose matrix:

```bash
docker compose -f docker/compose/docker-compose.yml run --rm py312-node22
```

The Compose matrix is intentionally not part of the default CI path. It provides extra Linux coverage for Python 3.10/3.11/3.12 and Node 20/22 without pretending to test Windows or macOS through Docker.

## GitHub Actions

Workflow: `.github/workflows/multiplatform.yml`.

The matrix runs:

- `linux-docker / ubuntu-latest`
- `windows-runner / windows-latest`
- `macos-runner / macos-latest`
- `linux-installer-gui / ubuntu-latest`
- `windows-installer-gui / windows-latest`
- `macos-installer-gui / macos-latest`

The workflow checks out this test repository, installs Python and Node, fetches and installs `urirun`, runs the full test suite, uploads `reports/`, uploads `reports/junit.xml`, and writes a readable GitHub Actions summary.

## End-User Installer and GUI Coverage

The existing suite covers CLI, registry, permissions, connectors and transport
smoke tests. The user journey suite adds the end-user path:

- build/package `urirun` into product artifacts such as wheels and sdists;
- create a local deployment simulation with a manifest and checksums;
- open `https://get.urirun.com/` in Chromium through Playwright;
- download/hash the platform installer script;
- optionally execute the remote installer in an isolated HOME/USERPROFILE when
  `GET_URIRUN_ALLOW_REMOTE_INSTALL=1`;
- run `urirun --version`, `urirun doctor --json` and a basic CLI command;
- start `urirun host dashboard serve`;
- open the dashboard in Playwright, click visible UI controls, and fail on
  JavaScript console errors or failed network requests.

The HTTP transport test is not a GUI test. It checks `/health` and `/run` on an
HTTP node. The GUI test starts the operator dashboard, opens a real browser,
clicks UI controls, records screenshots and Playwright trace diagnostics, and
checks browser/runtime failures.

Product artifacts are files a user or deployment flow consumes: installers,
packages, wheels, sdists, `.exe` files, checksums and manifests. Screenshots,
Playwright traces, stdout/stderr logs, JSON reports and JUnit XML are diagnostic
test artifacts, not product artifacts.

The local promotion intermediate format is `reports/deployment-bundle/`:

- `manifest.json`
- `artifacts/`
- `checksums/SHA256SUMS`
- `site/index.html`
- `deployment-report.json`

The bundle is a dry-run promotion candidate only. Production deployment remains a trusted external CI/CD job with explicit credentials, signing, and approval.

Run only the user journey locally:

```bash
python scripts/run_tests.py tests/test_product_artifacts_deployment.py tests/test_get_urirun_site.py tests/test_get_urirun_install_flow.py tests/test_gui_user_journey.py
```

Linux/macOS remote installer execution:

```bash
GET_URIRUN_ALLOW_REMOTE_INSTALL=1 python scripts/run_tests.py tests/test_get_urirun_install_flow.py
```

Windows PowerShell remote installer execution:

```powershell
$env:GET_URIRUN_ALLOW_REMOTE_INSTALL="1"
python scripts\run_tests.py tests\test_get_urirun_install_flow.py
```

Local-source install flow without executing the production installer:

```bash
GET_URIRUN_INSTALL_MODE=local-repo python scripts/run_tests.py tests/test_get_urirun_install_flow.py
```

Architecture and flow diagrams: [docs/multiplatform-e2e-design.md](docs/multiplatform-e2e-design.md).

## Documentation

- **[docs/IMPLEMENTED.md](docs/IMPLEMENTED.md)** - Detailed description of implemented test areas, platform coverage, environment variables, and reports
- **[docs/TODO.md](docs/TODO.md)** - Structured plan for remaining work, critical TODOs, and external blockers
- **[docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md)** - Generated self-validation status table
- **[docs/gui-test-contract.md](docs/gui-test-contract.md)** - Dashboard selector, browser error, screenshot, trace, and video contract
- **[docs/ci-verification.md](docs/ci-verification.md)** - How to run and record GitHub Actions verification
- **[docs/docker-compose-matrix.md](docs/docker-compose-matrix.md)** - Optional Linux Compose matrix usage
- **[docs/external-contracts/main-urirun.md](docs/external-contracts/main-urirun.md)** - Required contracts for the main `urirun` repository
- **[docs/external-contracts/get-urirun-com.md](docs/external-contracts/get-urirun-com.md)** - Required contracts for the install site repository
- **[docs/external-contracts/production-promotion.md](docs/external-contracts/production-promotion.md)** - Trusted production promotion contract

## Self-Hosted Runners

Self-hosted runner setup guides:

- [Windows self-hosted runner](docs/self-hosted-runners/windows.md)
- [macOS self-hosted runner](docs/self-hosted-runners/macos.md)
- [Linux self-hosted runner](docs/self-hosted-runners/linux.md)
- [Manual-only workflow examples](docs/self-hosted-runners/workflow-examples.md)

Use these when replacing GitHub-hosted runners with company-managed Windows, macOS, or Linux hosts.

## Reports

Generated reports live in `reports/`:

- `summary.json` - OS, Python, Node, `urirun`, install metadata, and artifact list.
- `junit.xml` - pytest JUnit report for CI systems.
- `install-warning.json` - recorded when `urirun` package dependency resolution needs fallback handling.
- `transport-*.json` - structured transport failure reports with server/client logs.
- `*.stdout.log` and `*.stderr.log` - server process logs for transport tests.
- `product-artifacts/` - product artifacts built by the user journey profile.
- `deployment-bundle/` - promotion-candidate bundle with manifest, artifacts, checksums, site stub, and deployment report.
- `local-deployment/artifacts/manifest.json` - legacy local deployment simulation manifest with product artifact checksums.
- `screenshots/` and `traces/` - diagnostic Playwright artifacts, not product artifacts.
- `validation-report.json` - generated self-validation report.
- `ci-summary.md` - Markdown report intended for GitHub Actions step summary.
- `get-urirun-site.json`, `get-urirun-install.json`, `gui-user-journey.json`, `product-artifacts-deployment.json`, `local-dev-site.json`, `site-artifact-comparison.json` - user journey reports.

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
- Deployment-bundle dry-run promotion candidate generation.
- Configurable GUI console/network allowlists and Playwright trace/video retention.

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
- Recorded GitHub Actions verification for all six workflow profiles.
- Real platform installer artifact production remains outside this repository until the main `urirun` build pipeline provides those artifacts.
- Real local `get-urirun-com` serving remains PARTIAL until that repository exposes a stable dev/static server contract.

## External Blockers In Main `urirun`

These items depend on changes in the main `urirun` repository and should not be hidden or pretended fixed in this test repository:

- Remove the installation fallback after `urirun` publishes or vendors all dependencies declared by `adapters/python/pyproject.toml` (`urirun-contract`, `urirun-connector-router`, `urirun-flow`, and version constraints).
- Remove the `xfail` from `connectors show planfile` after the main `urirun` CLI handler supports the command exposed by its parser.
- Promote gRPC transport coverage from experimental to stable only after the tested `urirun` install path consistently includes the required optional `grpcio` dependency on all target platforms.
