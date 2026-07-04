# Desktop-in-a-box test node for kvm:// E2E scenarios.
#   Xvfb (virtual X) -> openbox (WM) -> x11vnc -> noVNC/websockify (live view)
#   + a real `urirun node serve --execute` with urirun-connector-kvm inside.
# The harness drives the desktop ONLY through mesh URIs (kvm://, app://);
# noVNC on :6080 is the human-observable window into the same X display.
#
# The urirun dependency chain (urirun-contract/-connector-router/-flow) is not
# published on PyPI yet, so the wheels are vendored under ./vendor and must be
# rebuilt (scripts in tests/test_desktop_kvm.py docstring) when urirun changes.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl procps \
      python3 python3-venv python3-pip \
      xvfb x11-utils openbox x11vnc novnc websockify \
      xdotool wmctrl scrot imagemagick tesseract-ocr \
      lxterminal mousepad xterm fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/ /opt/vendor/
# The urirun wheel bundles a STALE copy of urirun_connector_router (upstream
# packaging bug: the dependency is both declared and vendored). Install the
# core first, then the real dependency wheels so their files win the clobber.
RUN python3 -m venv /opt/urirun \
    && /opt/urirun/bin/pip install --no-cache-dir -U pip \
    && /opt/urirun/bin/pip install --no-cache-dir --no-deps /opt/vendor/urirun-0*.whl \
    && /opt/urirun/bin/pip install --no-cache-dir \
         /opt/vendor/urirun_contract-*.whl /opt/vendor/urirun_connector_router-*.whl \
         /opt/vendor/urirun_flow-*.whl /opt/vendor/urirun_connector_kvm-*.whl \
         jsonschema pydantic mss Pillow pytesseract \
    && /opt/urirun/bin/python -c "import urirun.node.mesh" \
    && /opt/urirun/bin/urirun --version

COPY entrypoint.sh /usr/local/bin/desktop-pc
RUN chmod +x /usr/local/bin/desktop-pc

# 6080 = noVNC (browser view); 8765 = urirun node API
EXPOSE 6080 8765
ENTRYPOINT ["/usr/local/bin/desktop-pc"]
