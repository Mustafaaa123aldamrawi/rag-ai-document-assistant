from pathlib import Path


def test_api_uses_single_canonical_professional_report_engine():
    source = (
        Path(__file__).resolve().parents[1] / "api" / "main.py"
    ).read_text(encoding="utf-8")

    assert (
        "from professional_reports import REPORT_TYPES, "
        "build_professional_project_report"
    ) in source
    assert "from project_reports import" not in source
    assert "build_professional_project_report_docx" not in source
    assert "build_report_docx(report)" in source
    assert 'safe_report_filename(report, "docx")' in source
