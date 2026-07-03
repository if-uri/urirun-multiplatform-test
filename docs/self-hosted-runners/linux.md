# Linux self-hosted runner

Linux can run the native runner profile and the Docker profile. The default GitHub Actions matrix uses Docker for Linux.

## System requirements

- Ubuntu 22.04/24.04 or another modern Linux distribution.
- Network access to GitHub and to the configured `URIRUN_REPO_URL`.
- At least 2 CPU cores and 4 GB RAM.
- Docker Engine for the `linux-docker` profile.

## Required tools

- Python 3.10 or newer; Python 3.12 is recommended.
- Node.js 22 or newer.
- Git 2.44 or newer.
- Docker 24 or newer with the runner user allowed to run Docker.
- Bash.

## Local pre-flight without Docker

```bash
git clone https://github.com/if-uri/urirun-multiplatform-test
cd urirun-multiplatform-test
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
python3 scripts/run_tests.py
```

## Local pre-flight with Docker

```bash
docker build -t urirun-linux-test -f docker/linux/Dockerfile .
docker run --rm -v "$PWD/reports:/workspace/reports" urirun-linux-test
```

## Runner labels

Example labels:

- `self-hosted`
- `linux`
- `x64`
- `docker`
- `urirun`

Example workflow fragment:

```yaml
runs-on: [self-hosted, linux, x64, docker, urirun]
shell: bash
```

## Common problems

- Docker permission denied: add the runner user to the `docker` group and restart the runner service.
- Docker daemon unavailable: verify `systemctl status docker` and `docker info`.
- Old Python: install Python 3.12 or use `actions/setup-python`.
- Old Node: install Node 22 or use `actions/setup-node`.
- Network restricted: allow GitHub, PyPI, and the configured `URIRUN_REPO_URL`.
- Reports missing after Docker run: mount `reports/` into `/workspace/reports`.
