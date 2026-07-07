# GUI Test Contract

This contract describes what the `urirun` dashboard should expose so the black-box GUI tests can remain stable while the UI evolves.

## Status

Current status: **EXPERIMENTAL**.

The harness supports stable selectors and strict browser error filtering, but the main dashboard may still emit console/network errors or lack `data-testid` attributes. Those gaps remain external to this repository.

## Required Dashboard Contract

- Stable entrypoint: `urirun host dashboard serve --project <path> --db <path> --host <host> --port <port>`.
- Health endpoint: `GET /api/health` should become ready before browser navigation.
- Stable selectors: prefer `data-testid` attributes for primary navigation and critical commands.
- Naming convention: lowercase kebab-case, for example `data-testid="chat"`, `data-testid="nodes"`, `data-testid="tasks"`, `data-testid="services"`, `data-testid="artifacts"`.
- Accessible fallback: controls should also have useful `aria-label` or role/name metadata.
- Fallback text selectors: accepted only as compatibility fallback while the dashboard contract is being adopted.

## Critical Flows

- Open dashboard home.
- Navigate or activate Chat, Nodes, Tasks, Services, and Artifacts.
- Keep the page responsive after each click.
- Avoid browser console errors and failed application requests during empty-project navigation.

## Browser Error Policy

The default policy is restrictive: every console error and failed request is critical unless explicitly allowed.

Configuration:

- `URIRUN_GUI_ALLOWED_CONSOLE_ERROR_PATTERNS`: newline- or semicolon-separated regular expressions for accepted console errors.
- `URIRUN_GUI_ALLOWED_NETWORK_ERROR_PATTERNS`: newline- or semicolon-separated regular expressions for accepted failed requests.

Reports split browser events into:

- `accepted_console_errors`
- `critical_console_errors`
- `accepted_failed_requests`
- `critical_failed_requests`

Tests fail only on critical errors. Known dashboard errors may remain `xfail` while the main `urirun` dashboard is being stabilized.

## Trace And Video Retention

- `URIRUN_PLAYWRIGHT_TRACE_MODE=always|on-failure|off`
- `URIRUN_PLAYWRIGHT_VIDEO_MODE=always|on-failure|off`

Default trace mode is `on-failure`. Default video mode is `off`.

Screenshots, traces, videos, stdout/stderr logs, JSON reports, and JUnit XML are diagnostic test artifacts. They are not product artifacts and must not be published as installable product outputs.
