# IMPLEMENTED

This document describes what has been implemented in the `urirun-multiplatform-test` repository.

## Overview

`urirun-multiplatform-test` is a standalone black-box smoke and E2E harness for `urirun`. It fetches a selected `urirun` version, installs it into a fresh virtualenv, runs real CLI and transport scenarios, and writes diagnostics to `reports/`. The repository validates Linux, Windows, and macOS behavior without pretending Windows/macOS are ordinary Docker targets.

## Implemented Test Areas

### CLI Smoke Tests
- **Installation verification**: `urirun --version` and `urirun doctor --json`
- **Help system**: Main command help and subcommand help exposure
- **Registry operations**: List, compile, validate, and tree commands
- **Agent operations**: `agent space` command
- **Error bindings**: `errors bindings` compile and list
- **Discovery**: Entry point discovery with `discover --out`
- **OpenAPI generation**: `gen openapi` from fixture registry
- **Command generation**: `add-command` for portable bindings
- **Node configuration**: `node init` and `node config` roundtrip
- **Host configuration**: `host init` and `host add-node` roundtrip
- **Compatibility**: `compat list` (experimental)

### Registry Tests
- **Registry compilation**: Compile fixture registry to JSON
- **Route execution**: Execute registry routes with `urirun run`
- **Invalid URI handling**: Non-zero exit for missing routes
- **Validation**: `validate` command on fixture registry

### Connector Smoke Tests
- **Connector doctor**: Load and inspect installed bindings
- **Connector install dry-run**: Safe installation attempts for planfile, sqlite-context, mqtt
- **Connector show planfile**: Planfile inspection (marked as expected failure due to CLI parser limitation)

### Permission/Allow-List Tests
- **Deny-by-default**: Execution without `--allow` is denied
- **Wrong allow-list**: Execution with incorrect `--allow` pattern is denied

### Path and Shell Tests
- **Native path separators**: Registry file paths accept platform-specific separators
- **Paths with spaces**: Paths with spaces and unicode are preserved
- **Relative paths**: Relative registry paths from workspace
- **Output paths with spaces**: Output directories with spaces work correctly
- **Shell integration**: bash, PowerShell, and Windows cmd.exe shell coverage

### HTTP Transport Test
- **HTTP node serve**: Start HTTP node with registry
- **Health endpoint**: `/health` returns 200
- **Run endpoint**: `/run` accepts JSON payload and returns response
- **Structured reporting**: Transport failure reports with server/client logs

### MCP Transport Test
- **MCP stdio tools**: `tools/call` over stdio
- **MCP serve**: MCP server with JSON-RPC framing
- **Policy integration**: MCP respects allow-list policy
- **Experimental**: Marked as experimental due to evolving MCP surface

### Optional/Experimental gRPC Test
- **gRPC server/client**: Roundtrip when optional `grpcio` is available
- **URI_GRPC_MAP**: Environment variable for gRPC endpoint mapping
- **Conditional execution**: Skipped if `grpcio` is not installed
- **Experimental**: Marked as experimental due to optional dependency

### Product Artifact Build
- **Python wheel build**: Build wheel from `adapters/python`
- **Python sdist build**: Build source distribution
- **Manifest generation**: `manifest.json` with version, sha256, and metadata
- **Checksum calculation**: SHA256 for all artifacts
- **Artifact metadata**: Size, kind (wheel/sdist), platform classification

### Local Deployment Simulation
- **Local deployment directory**: `reports/local-deployment/`
- **Artifact copying**: Copy built artifacts to deployment directory
- **Manifest with URLs**: Manifest includes artifact URLs
- **Index HTML**: Simple HTML page listing artifacts and manifest
- **Safe for CI**: Does not deploy to production without explicit credentials

### Production `get.urirun.com` Browser Smoke
- **Playwright browser test**: Open production site in Chromium
- **Content checks**: Verify mentions of urirun, Windows, Linux, macOS, install
- **Console error monitoring**: Detect JavaScript console errors
- **Network failure monitoring**: Detect failed network requests
- **Screenshot capture**: Full-page screenshot of home page
- **Experimental**: Marked as experimental due to production content changes

### Installer Script Detection/Download/Hash
- **Script detection**: Detect `.ps1` (Windows) or `.sh` (Linux/macOS) installers
- **URL extraction**: Extract installer URLs from page content
- **Download**: Download installer script to `reports/installer/`
- **SHA256 hashing**: Calculate hash of downloaded installer
- **Installer excerpt**: Save first 4000 characters for inspection
- **Multiple candidates**: Try multiple URL patterns if primary fails

### Optional Remote Installer Execution
- **Isolated environment**: Execute installer in isolated HOME/USERPROFILE
- **Shell execution**: PowerShell on Windows, bash on Linux/macOS
- **Post-install checks**: Verify `urirun --version`, `urirun doctor --json`, `urirun --help`
- **Conditional execution**: Only runs when `GET_URIRUN_ALLOW_REMOTE_INSTALL=1`
- **Local-repo mode**: Alternative safe installation from local source

### GUI/Dashboard User Journey Through Playwright
- **Dashboard start**: `urirun host dashboard serve` with isolated project
- **Health check**: Wait for `/api/health` endpoint
- **Browser navigation**: Open dashboard in Chromium
- **UI interaction**: Click visible UI controls (Chat, Nodes, Tasks, Services, Artifacts)
- **Console monitoring**: Detect JavaScript console errors
- **Network monitoring**: Detect failed network requests
- **Screenshot capture**: Screenshots before and after clicks
- **Trace recording**: Playwright trace with screenshots, snapshots, sources
- **Process logs**: Capture stdout/stderr from dashboard process
- **Experimental**: Marked as experimental due to evolving dashboard UI

### Reports and Diagnostics
- **summary.json**: OS, Python, Node, urirun, install metadata, artifact list
- **junit.xml**: pytest JUnit report for CI systems
- **install-warning.json**: Recorded when package dependency resolution needs fallback
- **transport-*.json**: Structured transport failure reports with server/client logs
- ***.stdout.log and *.stderr.log**: Server process logs for transport tests
- **urirun-errors.jsonl**: Error log file for policy denials and errors
- **JSON failure reports**: Per-test failure reports with system info and recommendations

### GitHub Actions Matrix
- **linux-docker**: Ubuntu-latest with Docker container
- **windows-runner**: Windows-latest with PowerShell
- **macos-runner**: macOS-latest with bash
- **linux-installer-gui**: Ubuntu-latest with user journey tests
- **windows-installer-gui**: Windows-latest with user journey tests
- **macos-installer-gui**: macOS-latest with user journey tests

## Platform Coverage

### Linux Docker
- **Profile**: `linux-docker`
- **Environment**: Docker container built from `docker/linux/Dockerfile`
- **Test scope**: Full CLI, registry, connector, permission, path, shell, transport tests
- **User journey**: Not included in linux-docker profile (separate linux-installer-gui profile)

### Windows Runner
- **Profile**: `windows-runner`
- **Environment**: GitHub Actions `windows-latest` runner
- **Test scope**: Full CLI, registry, connector, permission, path, shell, transport tests
- **Shell coverage**: PowerShell and cmd.exe
- **User journey**: Separate windows-installer-gui profile

### macOS Runner
- **Profile**: `macos-runner`
- **Environment**: GitHub Actions `macos-latest` runner
- **Test scope**: Full CLI, registry, connector, permission, path, shell, transport tests
- **Shell coverage**: bash
- **User journey**: Separate macos-installer-gui profile

### Linux Installer GUI
- **Profile**: `linux-installer-gui`
- **Environment**: GitHub Actions `ubuntu-latest` runner
- **Test scope**: Product artifacts, get.urirun.com site, install flow, GUI user journey
- **Browser**: Chromium via Playwright
- **Installer**: `.sh` script detection and execution

### Windows Installer GUI
- **Profile**: `windows-installer-gui`
- **Environment**: GitHub Actions `windows-latest` runner
- **Test scope**: Product artifacts, get.urirun.com site, install flow, GUI user journey
- **Browser**: Chromium via Playwright
- **Installer**: `.ps1` script detection and execution via PowerShell

### macOS Installer GUI
- **Profile**: `macos-installer-gui`
- **Environment**: GitHub Actions `macos-latest` runner
- **Test scope**: Product artifacts, get.urirun.com site, install flow, GUI user journey
- **Browser**: Chromium via Playwright
- **Installer**: `.sh` script detection and execution via bash

## Product Artifacts vs Diagnostic Artifacts

### Product Artifacts
Product artifacts are files a user or deployment flow consumes:

- **wheel**: Python wheel package (`.whl`)
- **sdist**: Python source distribution (`.tar.gz`)
- **manifest**: `manifest.json` with version, sha256, and artifact metadata
- **checksums**: SHA256 hashes for all artifacts
- **Future artifacts**: `.exe`, installers, platform packages (not yet implemented)

**Location**: `reports/product-artifacts/` and `reports/local-deployment/artifacts/`

### Diagnostic Artifacts
Diagnostic artifacts are test outputs for debugging and CI:

- **screenshots**: Playwright screenshots (`reports/screenshots/`)
- **traces**: Playwright trace files (`reports/traces/`)
- **logs**: stdout/stderr logs for transport tests (`reports/*.stdout.log`, `reports/*.stderr.log`)
- **JSON reports**: Structured test reports (`reports/*.json`)
- **JUnit XML**: CI-compatible test report (`reports/junit.xml`)
- **Error logs**: urirun error log (`reports/urirun-errors.jsonl`)

**Location**: `reports/` subdirectories

## Environment Variables

### Core urirun Configuration
- **URIRUN_REPO_URL**: Repository URL for the tested urirun; default `https://github.com/if-uri/urirun.git`
- **URIRUN_REF**: Branch, tag, or commit to test; default `main`
- **URIRUN_SOURCE_DIR**: Optional local checkout of urirun; useful for development
- **URIRUN_TEST_PROFILE**: Profile name, usually set by CI (linux-docker, windows-runner, macos-runner, installer-gui-e2e)
- **URIRUN_TEST_VENV**: Virtualenv path used by tests; normally set by `scripts/run_tests.py`

### get.urirun.com Configuration
- **GET_URIRUN_PRODUCTION_URL**: Production install site; default `https://get.urirun.com/`
- **GET_URIRUN_REPO_URL**: Local-dev install site repo; default `https://github.com/if-uri/get-urirun-com.git`
- **GET_URIRUN_REF**: Ref for the local-dev install site; default `main`
- **GET_URIRUN_SITE_MODE**: `production-site`, `local-dev-site`, or `both`; default `production-site`
- **GET_URIRUN_INSTALL_MODE**: `site`, `local-repo`, or `skip`; default `site`
- **GET_URIRUN_ALLOW_REMOTE_INSTALL**: `0` by default; set `1` only in trusted CI to execute remote installer scripts

### Deployment and GUI Configuration
- **URIRUN_ARTIFACTS_DIR**: Optional directory for product artifacts; default `reports/product-artifacts`
- **URIRUN_DEPLOYMENT_MODE**: `local-simulated` by default for safe CI; `production` is external CI/CD requirement
- **URIRUN_GUI_E2E**: Set `0` to skip GUI browser tests; default `1` in installer-gui-e2e profile

### Internal/Test Configuration
- **URIRUN_USER_JOURNEY_ACTIVE**: Set to `1` by `scripts/run_tests.py` when user journey tests are targeted
- **URIRUN_ERRORS**: Set to `1` to enable error logging
- **URIRUN_ERROR_LOG**: Path to error log file; default `reports/urirun-errors.jsonl`
- **PYTHONUTF8**: Set to `1` for UTF-8 encoding
- **PYTHONIOENCODING**: Set to `utf-8` for UTF-8 encoding

## Reports Generated

### Summary Reports
- **summary.json**: OS, Python, Node, urirun version, install metadata, artifact list
- **junit.xml**: pytest JUnit report for CI systems
- **install-warning.json**: Dependency resolution fallback warnings

### Transport Reports
- **transport-http-node.json**: HTTP transport test report
- **transport-mcp-tools.json**: MCP tools discovery report
- **transport-mcp-stdio.json**: MCP stdio transport report
- **transport-grpc.json**: gRPC transport report

### User Journey Reports
- **get-urirun-site.json**: Production site browser smoke test report
- **get-urirun-install.json**: Installer download and execution report
- **gui-user-journey.json**: GUI dashboard user journey report
- **product-artifacts-deployment.json**: Product artifact build and local deployment report
- **site-artifact-comparison.json**: Production vs local dev site artifact comparison

### Diagnostic Artifacts
- **reports/screenshots/**: Playwright screenshots (get-urirun-home.png, gui-home.png, gui-after-clicks.png)
- **reports/traces/**: Playwright trace files (gui-user-journey.zip)
- **reports/product-artifacts/**: Built product artifacts (wheel, sdist, manifest.json)
- **reports/local-deployment/**: Local deployment simulation (artifacts/, index.html)
- **reports/installer/**: Downloaded installer scripts (get-urirun-installer.ps1, get-urirun-installer.sh)
- **reports/*.stdout.log**: Server process stdout logs
- **reports/*.stderr.log**: Server process stderr logs
- **reports/urirun-errors.jsonl**: urirun error log file

## How to Run

### Full Default Suite
```bash
python scripts/run_tests.py
```

### User Journey Only
```bash
python scripts/run_tests.py tests/test_product_artifacts_deployment.py tests/test_get_urirun_site.py tests/test_get_urirun_install_flow.py tests/test_gui_user_journey.py
```

### Remote Installer Execution
Linux/macOS:
```bash
GET_URIRUN_ALLOW_REMOTE_INSTALL=1 python scripts/run_tests.py tests/test_get_urirun_install_flow.py
```

Windows PowerShell:
```powershell
$env:GET_URIRUN_ALLOW_REMOTE_INSTALL="1"
python scripts\run_tests.py tests\test_get_urirun_install_flow.py
```

### Local-Source Install Flow
```bash
GET_URIRUN_INSTALL_MODE=local-repo python scripts/run_tests.py tests/test_get_urirun_install_flow.py
```

### Docker Linux
```bash
docker build -t urirun-linux-test -f docker/linux/Dockerfile .
docker run --rm urirun-linux-test
```

With reports outside container:
```bash
docker run --rm -v "$PWD/reports:/workspace/reports" urirun-linux-test
```

## Stability Markers

- **stable**: Expected to pass across Linux Docker, Windows runner, and macOS runner
- **experimental**: Real coverage for a surface that may still depend on optional packages or evolving behavior
- **expected_failure**: Known behavior gap, normally paired with xfail
- **user_journey**: End-user installer and GUI/browser tests

## Self-Hosted Runner Documentation

- **Windows**: `docs/self-hosted-runners/windows.md`
- **macOS**: `docs/self-hosted-runners/macos.md`
- **Linux**: `docs/self-hosted-runners/linux.md`
