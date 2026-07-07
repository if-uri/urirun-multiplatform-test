from __future__ import annotations

from scripts import ci_summary, validate_repo


def test_validation_rows_use_known_statuses():
    rows = validate_repo.build_rows()
    statuses = {row["Current status"] for row in rows}
    assert statuses <= validate_repo.VALID_STATUSES
    assert any(row["Area"] == "Deployment bundle" for row in rows)
    assert any(row["Area"] == "GUI test contract and error policy" for row in rows)


def test_ci_summary_generation_handles_missing_reports(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr(ci_summary, "REPORT_DIR", reports)
    text = ci_summary.build_summary()
    assert "summary.json" in text
    assert "Validation" in text
    assert "Transport Reports" in text
