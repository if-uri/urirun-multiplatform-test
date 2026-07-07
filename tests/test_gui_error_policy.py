from __future__ import annotations

import pytest

from tests.gui_utils import classify_browser_events, retention_mode, selector_candidates, should_keep_artifact


def test_browser_error_allowlist_splits_accepted_and_critical(monkeypatch):
    monkeypatch.setenv("URIRUN_GUI_ALLOWED_CONSOLE_ERROR_PATTERNS", "ResizeObserver")
    monkeypatch.setenv("URIRUN_GUI_ALLOWED_NETWORK_ERROR_PATTERNS", "analytics")
    classified = classify_browser_events(
        {
            "console_errors": ["error: ResizeObserver loop completed", "error: app crashed"],
            "failed_requests": ["GET https://example.test/analytics net::ERR_BLOCKED", "GET /api/data net::ERR_FAILED"],
        }
    )
    assert classified["accepted_console_errors"] == ["error: ResizeObserver loop completed"]
    assert classified["critical_console_errors"] == ["error: app crashed"]
    assert classified["accepted_failed_requests"] == ["GET https://example.test/analytics net::ERR_BLOCKED"]
    assert classified["critical_failed_requests"] == ["GET /api/data net::ERR_FAILED"]


def test_retention_modes(monkeypatch):
    monkeypatch.setenv("URIRUN_PLAYWRIGHT_TRACE_MODE", "on-failure")
    assert retention_mode("URIRUN_PLAYWRIGHT_TRACE_MODE", "always") == "on-failure"
    assert should_keep_artifact("always", failed=False) is True
    assert should_keep_artifact("on-failure", failed=True) is True
    assert should_keep_artifact("on-failure", failed=False) is False
    assert should_keep_artifact("off", failed=True) is False


def test_invalid_retention_mode_fails(monkeypatch):
    monkeypatch.setenv("URIRUN_PLAYWRIGHT_TRACE_MODE", "sometimes")
    with pytest.raises(ValueError):
        retention_mode("URIRUN_PLAYWRIGHT_TRACE_MODE", "always")


def test_selector_candidates_prefer_stable_contract():
    candidates = selector_candidates("Chat")
    assert candidates[0] == '[data-testid="chat"]'
    assert candidates[-1] == "text=/Chat/i"
