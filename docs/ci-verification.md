# CI Verification Guide

Status: **NOT VERIFIED** until real GitHub Actions run evidence is recorded.

## Workflow

Workflow file: `.github/workflows/multiplatform.yml`.

Required profiles:

- `linux-docker`
- `windows-runner`
- `macos-runner`
- `linux-installer-gui`
- `windows-installer-gui`
- `macos-installer-gui`

## Manual Run

Open GitHub Actions for `urirun multiplatform e2e`, choose **Run workflow**, and set:

- `urirun_repo_url`: `https://github.com/if-uri/urirun.git` or a fork URL.
- `urirun_ref`: branch, tag, or commit to test.
- `allow_remote_install`: `false` for safe download/hash-only installer testing; `true` only in trusted CI.
- `get_urirun_site_mode`: `production-site`, `local-dev-site`, or `both`.

## Artifacts To Inspect

For every job, download the uploaded reports artifact and inspect:

- `reports/summary.json`
- `reports/junit.xml`
- `reports/validation-report.json`
- `reports/ci-summary.md`
- transport reports
- user journey reports for installer-gui jobs
- `reports/deployment-bundle/` for installer-gui jobs
- screenshots/traces for GUI jobs

## Updating Validation Docs

After a complete Actions run:

1. Record the workflow run URL and date.
2. Record each profile status: pass, fail, skipped, xfail-heavy, or infrastructure failure.
3. Update `docs/VALIDATION_REPORT.md` with the run evidence.
4. Update `docs/TODO_EXECUTION_STATUS.md` for items that move from `NOT VERIFIED` to verified.
5. Do not mark platform artifacts or production deployment `DONE` unless the external artifact/promotion contracts are also satisfied.

## Interpreting Failures

- A failure in current `urirun` behavior should be reported as product regression or external blocker, not hidden in this harness.
- A missing stable `get-urirun-com` dev command should remain `PARTIAL / EXTERNAL BLOCKER`.
- Remote installer execution should remain disabled unless the run is trusted and explicitly approved.
