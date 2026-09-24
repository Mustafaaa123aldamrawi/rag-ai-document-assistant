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
