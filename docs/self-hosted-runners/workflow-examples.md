# Self-Hosted Workflow Examples

Status: **DONE / NOT VERIFIED**.

The manual-only workflow `.github/workflows/self-hosted-examples.yml` demonstrates common labels:

- `[self-hosted, linux, urirun]`
- `[self-hosted, windows, urirun]`
- `[self-hosted, macos, urirun]`

## Host Requirements

- Python 3.12 or compatible `actions/setup-python` support.
- Node 22 or compatible `actions/setup-node` support.
- Git.
- Docker on Linux hosts if running the Docker profile.
- Browser dependencies if running installer/GUI jobs.
- Network access to clone `if-uri/urirun` and optional `if-uri/get-urirun-com`.

## Manual Run

Open the `self-hosted runner examples` workflow and select:

- `linux`
- `windows`
- `macos`

These examples are not part of default CI. Organization-specific labels may differ.

## Verification

Do not mark self-hosted coverage as verified until a real run URL and report artifacts are recorded in `docs/VALIDATION_REPORT.md`.
