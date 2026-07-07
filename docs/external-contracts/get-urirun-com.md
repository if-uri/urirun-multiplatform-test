# `if-uri/get-urirun-com` External Contract

Status: **EXTERNAL BLOCKER / PARTIAL** for full local-dev-site validation.

This harness can clone the site repository, copy a local `deployment-bundle`, detect common dev server patterns, and run a smoke fetch when a stable command exists. Full validation requires the site repository to expose a stable contract.

## Stable Dev Server Command

The site repository should provide one of:

- `package.json` script: `dev`
- `package.json` script: `start`
- static `index.html` at repository root
- static `public/index.html`

The preferred command should accept host/port arguments or document equivalent environment variables. Expected defaults:

- host: `127.0.0.1`
- port: dynamic port supplied by the harness

## Local Artifact Injection

The harness copies:

- `deployment-bundle/`
- `artifacts/<artifact-name>`

The site should document where local artifacts must be placed and how they are served. Recommended URL templates:

- manifest: `/manifest.json` or `/deployment-bundle/manifest.json`
- checksums: `/checksums/SHA256SUMS` or `/deployment-bundle/checksums/SHA256SUMS`
- artifacts: `/artifacts/{name}` or `/deployment-bundle/artifacts/{name}`

## Manifest Contract

The site should publish a machine-readable manifest with:

- `product`
- `version`
- `repo_url`
- `ref`
- `revision`
- `generated_at`
- `artifacts[]`
- `checksums`

Each artifact should include:

- `name`
- `kind`
- `platform`
- `url`
- `sha256`
- `size`

## Installer Links

The page should expose stable links for:

- Windows PowerShell installer: `.ps1`
- Linux shell installer: `.sh`
- macOS shell/pkg installer: `.sh` or `.pkg`

Links should be discoverable through real `href` attributes, not only prose.

## Playwright Selectors

Install actions should expose stable selectors:

- `data-testid="install-windows"`
- `data-testid="install-linux"`
- `data-testid="install-macos"`
- `data-testid="download-manifest"`
- `data-testid="download-checksums"`

## Current Harness Behavior

If this contract is missing, the local-dev-site test writes `reports/local-dev-site.json` and xfails with `integration_required` rather than hard failing or claiming success.
