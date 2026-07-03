from __future__ import annotations

import json
import os

import pytest

from tests.gui_utils import SCREENSHOT_DIR, current_system, monitor_page, require_playwright, write_json_report


pytestmark = pytest.mark.skipif(
    os.environ.get("URIRUN_USER_JOURNEY_ACTIVE") != "1",
    reason="user journey tests run only in installer-gui-e2e/user-journey profile or when explicitly targeted through scripts/run_tests.py",
)


@pytest.mark.user_journey
@pytest.mark.experimental
def test_get_urirun_home_page_browser_smoke():
    sync_playwright = require_playwright()
    url = os.environ.get("GET_URIRUN_PRODUCTION_URL") or os.environ.get("GET_URIRUN_URL", "https://get.urirun.com/")
    report = {
        "url": url,
        "system": current_system(),
        "http_status": None,
        "title": None,
        "content_checks": {},
        "console_errors": [],
        "failed_requests": [],
        "screenshot": str(SCREENSHOT_DIR / "get-urirun-home.png"),
        "recommendation": "Verify get.urirun.com renders install instructions for Linux, Windows and macOS without browser console or network failures.",
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        events = monitor_page(page)
        try:
            response = page.goto(url, wait_until="networkidle", timeout=60_000)
            report["http_status"] = None if response is None else response.status
            report["title"] = page.title()
            text = page.locator("body").inner_text(timeout=15_000)
            lower = text.lower()
            report["content_checks"] = {
                "mentions_urirun": "urirun" in lower,
                "mentions_windows": "windows" in lower or "powershell" in lower,
                "mentions_linux": "linux" in lower or "bash" in lower or "curl" in lower,
                "mentions_macos": "macos" in lower or "mac os" in lower or "darwin" in lower or "brew" in lower,
                "mentions_install": "install" in lower or "installer" in lower or "install.ps1" in lower or "install.sh" in lower,
            }
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=report["screenshot"], full_page=True)
        finally:
            report["console_errors"] = events["console_errors"]
            report["failed_requests"] = events["failed_requests"]
            write_json_report("get-urirun-site.json", report)
            browser.close()

    assert report["http_status"] and 200 <= int(report["http_status"]) < 400
    assert all(report["content_checks"].values()), json.dumps(report["content_checks"], indent=2)
    assert report["console_errors"] == []
    assert report["failed_requests"] == []
