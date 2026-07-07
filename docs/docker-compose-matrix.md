# Optional Docker Compose Matrix

Status: **PARTIAL / NOT VERIFIED** until run evidence is recorded.

The Compose matrix is Linux-only optional coverage. It does not replace Windows or macOS runner testing.

## Services

- `py310-node20`
- `py311-node22`
- `py312-node22`

## Run

```bash
docker compose -f docker/compose/docker-compose.yml run --rm py312-node22
```

Run all services:

```bash
docker compose -f docker/compose/docker-compose.yml up --build --abort-on-container-exit
```

## Reports

Reports are mounted to:

```text
reports/
```

Inspect:

- `reports/summary.json`
- `reports/junit.xml`
- `reports/validation-report.json`
- `reports/ci-summary.md`

## Constraints

- Do not use this to claim Windows/macOS coverage.
- Do not add heavy language SDKs unless a specific `urirun` E2E path requires them.
- Do not add it to default CI unless runtime cost is acceptable.
