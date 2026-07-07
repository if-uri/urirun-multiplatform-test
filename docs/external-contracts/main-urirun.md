# Main `if-uri/urirun` External Contract

Status: **EXTERNAL BLOCKER** for the `urirun-multiplatform-test` repository.

This test harness can validate built artifacts and installed behavior, but it cannot create product capabilities that must live in the main `if-uri/urirun` repository.

## Required Artifact Pipelines

The main repository should publish signed or otherwise verifiable outputs for:

- Windows installer or executable, for example `urirun-<version>-windows-x64.exe`.
- Linux packages, for example `.deb`, `.rpm`, AppImage, or `urirun-<version>-linux-x64.tar.gz`.
- macOS package or application bundle, for example `.pkg`, `.app`, or a Homebrew formula.
- Python wheel and sdist, which are already the only artifacts this harness can build locally today.

Each artifact should provide:

- `name`
- `version`
- `platform`
- `kind`
- `size`
- `sha256`
- download URL
- signing/notarization metadata where applicable

## Signing And Notarization

Windows and macOS artifacts should define:

- signing identity owner,
- timestamping policy,
- certificate/secrets storage,
- revocation/rotation process,
- macOS notarization and stapling steps if `.pkg` or `.app` artifacts are used.

## GUI/Dashboard Contract

The dashboard should expose:

- stable command: `urirun host dashboard serve --project <path> --db <path> --host <host> --port <port>`,
- health endpoint: `GET /api/health`,
- stable `data-testid` selectors using lowercase kebab-case,
- useful `aria-label` or role/name metadata for controls,
- stable critical navigation targets: `chat`, `nodes`, `tasks`, `services`, `artifacts`,
- no critical console errors or failed application requests during empty-project navigation.

The harness currently falls back to text selectors because this contract is not guaranteed.

## Dependency Publication Policy

The main package install should not require this harness to mask dependency resolution failures. Publish or vendor every runtime dependency required by `adapters/python/pyproject.toml`, including connector/runtime packages and compatible version constraints.

## gRPC Policy

The main repository should decide whether gRPC is:

- a first-class dependency installed by default, or
- an optional extra with a documented install path and platform support matrix.

Until then, gRPC coverage remains experimental in this harness.

## Acceptance Signal For This Harness

This harness can promote related statuses only after the main repository provides real artifacts and a documented manifest/release output. Until then, native platform artifacts and stable GUI selector adoption remain `EXTERNAL BLOCKER`.
