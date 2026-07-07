# Trusted Production Promotion Contract

Status: **DOCUMENTED ONLY / EXTERNAL BLOCKER**.

The `urirun-multiplatform-test` repository must not deploy production by default. It prepares and validates a local `deployment-bundle` that can be consumed by a separate trusted promotion job.

## Input

The promotion job should consume:

```text
reports/deployment-bundle/
  manifest.json
  artifacts/
  checksums/SHA256SUMS
  site/index.html
  deployment-report.json
```

The job must require `deployment-report.json` to have:

- `promotion_candidate: true`
- no validation problems
- expected artifact kinds for the target release channel

## Required Controls

- GitHub Environment or equivalent approval gate.
- Release credentials stored as secrets.
- Signing keys stored in a dedicated secret manager.
- Least-privilege deployment token.
- Audit logs for artifact upload, signing, manifest publish, and rollback.

## Publishing Targets

The owning deployment system should define the real targets, for example:

- GitHub Releases,
- PyPI,
- S3 or object storage,
- CDN-backed static site,
- package repositories for Linux,
- macOS/Windows installer distribution channels.

## Signing

Signing should happen in the trusted promotion job, not in this black-box test harness. The job should publish signature/notarization metadata in the production manifest.

## Rollback

The promotion job should define:

- previous manifest retention,
- artifact immutability policy,
- rollback command or manual procedure,
- smoke test requirements after rollback.

## Post-Publish Smoke Tests

After publishing, a separate smoke job should:

- fetch production manifest and checksums,
- verify artifact HTTP status and SHA256,
- fetch installer links,
- run safe install checks in isolated environments,
- run dashboard GUI smoke tests where supported.

## Explicit Non-Goals For This Harness

This repository should not:

- publish production artifacts automatically,
- hold production deployment secrets,
- sign binaries,
- mutate CDN/storage/GitHub Releases,
- mark production deployment as `DONE` without external job evidence.
