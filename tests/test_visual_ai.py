from pathlib import Path
from visual_ai import (
    build_visual_analysis_messages,
    build_visual_evidence_text,
    parse_visual_analysis,
)


def test_parse_visual_analysis_normalizes_unknown_category():
    result = parse_visual_analysis(
        '{"category":"mystery","summary":"x","visible_text":[],"devices":[],"observations":[],"possible_issues":[],"uncertainties":[]}'
    )
    assert result["category"] == "OTHER"


def test_parse_visual_analysis_accepts_embedded_json():
    result = parse_visual_analysis(
        'Result: {"category":"ERROR_SCREENSHOT","summary":"Error visible","visible_text":["No signal"],"devices":[],"observations":[],"possible_issues":[],"uncertainties":[]}'
    )
    assert result["category"] == "ERROR_SCREENSHOT"
    assert result["visible_text"] == ["No signal"]


def test_visual_evidence_preserves_uncertainty():
    text = build_visual_evidence_text(
        {
            "category": "AV_EQUIPMENT",
            "summary": "Rack equipment is visible.",
            "visible_text": [],
            "devices": [],
            "observations": ["A rack-mounted device is visible."],
            "possible_issues": [],
            "uncertainties": ["Model number is unreadable."],
        },
        file_name="rack.jpg",
    )
    assert "Model number is unreadable." in text
    assert "Critical details must be verified" in text


def test_visual_prompt_forbids_model_guessing():
    messages = build_visual_analysis_messages(
        file_name="device.jpg",
        image_data_url="data:image/jpeg;base64,abc",
    )
    user_text = messages[1]["content"][0]["text"]
    assert "Do not guess model numbers from appearance alone." in user_text



def test_app_routes_visual_analysis_to_dedicated_vision_llm():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "def call_vision_llm(" in app_source
    assert '"Qwen/Qwen3.8-Flash-Next:featherless-ai"' in app_source
    assert '"Qwen/Qwen2.5-VL-3B-Instruct"' in app_source
    assert "raw_visual_analysis = call_vision_llm(" in app_source
    visual_block = app_source.split(
        "# Process standalone site photos and screenshots",
        1,
    )[1]
    assert "raw_visual_analysis = call_conversation_llm(" not in visual_block



def test_vision_errors_keep_all_model_attempts_visible():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "attempt_errors = []" in app_source
    assert '"No compatible image-capable model succeeded. "' in app_source



def test_visual_questions_mark_subject_found_from_visual_evidence():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "visual_evidence_available = bool(" in app_source
    assert "if visual_evidence_available:" in app_source
    assert "subject_found = True" in app_source


def test_visual_grounding_rules_prevent_document_not_found_fallback():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "Visual grounding rules:" in app_source
    assert "Do not say the information was not found in the document when visual evidence is present." in app_source



def test_visual_reference_query_detection_exists_and_covers_image_language():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "def is_visual_reference_query(question):" in app_source
    assert '"this image"' in app_source
    assert '"this screenshot"' in app_source
    assert '"هذه الصورة"' in app_source


def test_visual_reference_with_visual_evidence_overrides_casual_routing():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "visual_evidence_present = any(" in app_source
    assert "visual_reference_query = (" in app_source
    assert 'router_intent = "DOCUMENT"' in app_source
    assert 'query_route = "DOCUMENT"' in app_source
