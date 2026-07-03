# TODO

This document outlines the remaining work and future improvements for the `urirun-multiplatform-test` repository.

## Critical TODO

### 1. Real Local `get-urirun-com` Dev Server

Currently, the local `get-urirun-com` is partially prepared/simulated. The test harness clones the repository and copies artifacts, but does not run a real local dev/static server.

**Required work:**
- Detect the actual stack used by the `get-urirun-com` repository (e.g., Next.js, Hugo, Jekyll, static HTML)
- Identify the stable dev server command (e.g., `npm run dev`, `python -m http.server`, `hugo serve`)
- Wire the locally built product artifacts into the dev server's artifact serving path
- Test the local dev server with the same Playwright/install flow as production
- If the repository lacks a stable start command, document the required contract for integration

**Impact:** Without this, the local-dev-site mode cannot fully validate the pre-production deployment flow.

### 2. Full Platform Product Artifacts

Currently, the product artifact build primarily creates Python wheel and sdist files. Platform-specific installers and executables are not yet built.

**Required work:**
- Verify whether the main `urirun` repository has a pipeline for building `.exe` installers for Windows
- Verify whether the main `urirun` repository has a pipeline for building platform packages for Linux (e.g., `.deb`, `.rpm`, AppImage)
- Verify whether the main `urirun` repository has a pipeline for building packages for macOS (e.g., `.pkg`, `.app`, Homebrew formula)
- If these pipelines exist, integrate them into `test_product_artifacts_deployment.py`
- If they do not exist, document the required build contract and artifact format

**Impact:** Without platform-specific artifacts, the user journey cannot validate the complete end-to-end installation experience for each platform.

### 3. Production Deployment Contract

The test harness should not deploy to production without explicit credentials and approval, but it must clearly define the production deployment contract.

**Required work:**
- Define which artifacts must be published to production (wheel, sdist, installers, manifest, checksums)
- Specify where artifacts are published (e.g., PyPI, S3, GitHub Releases, CDN)
- Specify how `get.urirun.com` detects and references published artifacts
- Define the required manifest format and checksum verification process
- Add a test that verifies the production deployment contract without actually deploying (e.g., dry-run validation)

**Impact:** Without a clear contract, it is difficult to validate that production deployments are consistent and complete.

### 4. CI Verification

Verify and document the actual results of GitHub Actions runs for all platform profiles.

**Required work:**
- Run and verify `linux-docker` profile on GitHub Actions
- Run and verify `windows-runner` profile on GitHub Actions
- Run and verify `macos-runner` profile on GitHub Actions
- Run and verify `linux-installer-gui` profile on GitHub Actions
- Run and verify `windows-installer-gui` profile on GitHub Actions
- Run and verify `macos-installer-gui` profile on GitHub Actions
- Document any platform-specific failures or quirks
- Add platform-specific workarounds if needed

**Impact:** Without CI verification, it is unclear which profiles actually pass in the CI environment.

## Important TODO

### 5. Better Production vs Dev Site Comparison

The current site artifact comparison is basic. It only counts references and does not perform deep validation.

**Improvements:**
- Compare actual artifact URLs between production and local dev
- Compare manifest structures and checksums
- Validate that production references point to existing artifacts
- Add diff-style reporting for easier debugging
- Validate that local dev artifacts are correctly wired into the dev server

### 6. Enhanced Manifest Comparison

The current manifest comparison is minimal. It should provide more detailed validation.

**Improvements:**
- Compare version fields between manifests
- Compare artifact lists and checksums
- Validate that all required artifact kinds are present
- Check for orphaned artifacts in the deployment directory
- Add schema validation for manifest.json

### 7. More Stable GUI Selectors

The current GUI selectors are simple text-based matches. They may break if the dashboard UI changes significantly.

**Improvements:**
- Use more specific selectors (e.g., data-testid attributes, CSS classes)
- Add fallback selectors for robustness
- Document the required UI contract for the dashboard
- Add visual regression testing if feasible

### 8. Whitelist Acceptable Network/Console Errors

The current GUI test fails on any console error or network failure. Some errors may be acceptable (e.g., third-party tracking failures).

**Improvements:**
- Identify and whitelist known benign errors (e.g., analytics, tracking pixels)
- Add configurable error filtering
- Document which errors are considered acceptable
- Separate critical errors from non-critical warnings

### 9. Optional Trace/Video Retention Policy

Currently, Playwright traces are always saved. For long-running CI, this may consume significant storage.

**Improvements:**
- Add configurable trace retention (e.g., save only on failure)
- Add optional video recording
- Add trace compression or cleanup policies
- Document the retention policy

### 10. Self-Hosted Runner Workflow Variants

The current self-hosted runner documentation is generic. Organization-specific variants may be needed.

**Improvements:**
- Add example workflow variants for common runner labels
- Document how to customize the matrix for self-hosted runners
- Add examples for runner-specific environment variables
- Document runner-specific prerequisites (e.g., Docker on Windows)

### 11. Docker Compose Matrix Coverage

The current Docker coverage is limited to a single Linux container. More comprehensive matrix coverage would be useful.

**Improvements:**
- Add Docker Compose configuration for multiple Linux distributions
- Mirror more of `urirun/examples/matrix` without pulling unrelated language SDK runtimes
- Add matrix variants for different Python versions
- Add matrix variants for different Node versions

## External Blockers

### Main `urirun` Repository

These items depend on changes in the main `urirun` repository:

#### Full Pipeline for Platform Artifacts
- **Issue**: The main `urirun` repository may not have a complete pipeline for building `.exe` installers, platform packages, or macOS bundles.
- **Impact**: The test harness cannot validate platform-specific installation flows.
- **Required**: Define and implement build pipelines for Windows `.exe`, Linux packages, and macOS packages.

#### Stable GUI/Web UI Entry Point
- **Issue**: The dashboard UI is evolving, and selectors may break.
- **Impact**: GUI tests may fail due to UI changes rather than actual regressions.
- **Required**: Stabilize the dashboard UI contract and add test-friendly attributes (e.g., data-testid).

#### Remove Installation Fallback
- **Issue**: The test harness uses a `--no-deps` fallback when package dependency resolution fails.
- **Impact**: This masks dependency issues in the main `urirun` package.
- **Required**: Publish or vendor all dependencies declared by `adapters/python/pyproject.toml` (urirun-contract, urirun-connector-router, urirun-flow, and version constraints).

#### Remove xfail for `connectors show planfile`
- **Issue**: The `connectors show planfile` command is exposed by the parser but rejected by the command handler.
- **Impact**: The test is marked as expected failure.
- **Required**: Implement the command handler for `connectors show planfile` in the main `urirun` CLI.

#### Promote gRPC from Experimental to Stable
- **Issue**: gRPC transport is marked as experimental because it depends on optional `grpcio`.
- **Impact**: gRPC coverage is not guaranteed across all platforms.
- **Required**: Ensure that the tested `urirun` install path consistently includes `grpcio` on all target platforms, or make gRPC a first-class dependency.

### `get-urirun-com` Repository

These items depend on changes in the `get-urirun-com` repository:

#### Stable Dev Server Command
- **Issue**: The repository may not have a stable, documented dev server command.
- **Impact**: The test harness cannot run a real local dev server.
- **Required**: Provide a stable command (e.g., `npm run dev`, `python -m http.server`) and document the port and serving directory.

#### Contract for Local Artifacts
- **Issue**: The contract for wiring local product artifacts into the dev server is unclear.
- **Impact**: The test harness cannot validate the pre-production deployment flow.
- **Required**: Document where to place local artifacts and how the dev server should serve them.

#### Manifest/Version/Checksum Contract
- **Issue**: The format and location of the manifest, version, and checksum files may not be standardized.
- **Impact**: The test harness cannot validate deployment consistency.
- **Required**: Define a standard manifest format with version, checksums, and artifact URLs.

#### Stable Page Selectors/Elements
- **Issue**: The install page structure may change, breaking Playwright selectors.
- **Impact**: Browser tests may fail due to page structure changes.
- **Required**: Stabilize the page structure and add test-friendly attributes (e.g., data-testid for download buttons).

#### Clear Links to Platform Installers
- **Issue**: The page may not have clear, stable links to Windows/Linux/macOS installers.
- **Impact**: The installer detection logic may fail.
- **Required**: Ensure that the page has stable, detectable links to platform-specific installers (e.g., `/install.ps1`, `/install.sh`).

## Nice to Have

### 12. Badge for `installer-gui-e2e` Profile

Add a separate CI badge for the installer-gui-e2e profile to distinguish it from the core CLI tests.

### 13. Markdown Report After CI

Generate a human-readable markdown report after each CI run, summarizing test results, artifacts, and any failures.

### 14. Automatic Screenshot Comparison

Add automatic screenshot comparison between production and dev site to detect visual regressions.

### 15. Automatic Issue Creation on Regression

Automatically create GitHub issues when regressions are detected in CI (e.g., failed tests, new console errors).

### 16. Nightly Schedule for Production Testing

Add a nightly GitHub Actions schedule to test the production site and detect production regressions.

### 17. Matrix for Python/Node Versions

Add a matrix for different Python versions (e.g., 3.10, 3.11, 3.12) and Node versions to ensure compatibility.

### 18. Performance Benchmarks

Add performance benchmarks for CLI commands and transport operations to detect performance regressions.

### 19. Coverage Reporting

Add code coverage reporting for the test harness itself to ensure test quality.

### 20. Parallel Test Execution

Optimize test execution by running independent tests in parallel to reduce CI runtime.
