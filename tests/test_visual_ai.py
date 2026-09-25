from pathlib import Path
from visual_ai import (
    build_visual_analysis_messages,
    build_visual_diagnostic_context,
    build_visual_diagnostic_plan,
    build_visual_evidence_text,
    build_visual_field_answer,
    parse_visual_analysis,
    visual_answer_is_complete,
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



def test_visual_diagnostic_plan_states_no_obvious_fault_when_none_supported():
    analysis = {
        "category": "SITE_PHOTO",
        "summary": "A curved display is active and showing a desktop.",
        "visible_text": [],
        "devices": [],
        "observations": [
            "A large curved display is active.",
            "A desktop image is visible across the display.",
        ],
        "possible_issues": [],
        "uncertainties": [
            "Manufacturer and model are not readable.",
        ],
    }

    plan = build_visual_diagnostic_plan(
        analysis,
        question="What can you see, what looks wrong, and what should I check next?",
    )

    assert plan["visible_fault_status"] == "NO_OBVIOUS_VISIBLE_FAULT"
    assert "No obvious visual fault" in plan["fault_summary"]
    assert any("geometry" in item.lower() for item in plan["next_checks"])
    assert any("brightness" in item.lower() for item in plan["next_checks"])
    assert not any("manufacturer" in item.lower() for item in plan["next_checks"])


def test_visual_diagnostic_plan_preserves_possible_issue_confidence():
    analysis = {
        "category": "SITE_PHOTO",
        "summary": "Display image is visible.",
        "visible_text": [],
        "devices": [],
        "observations": ["A vertical discontinuity is visible."],
        "possible_issues": [
            {
                "issue": "Visible vertical discontinuity across the display image.",
                "confidence": "medium",
                "basis": "The line is visible across adjacent image areas.",
            }
        ],
        "uncertainties": [],
    }

    plan = build_visual_diagnostic_plan(analysis)

    assert plan["visible_fault_status"] == "POSSIBLE_VISIBLE_FAULT"
    assert plan["possible_issues"][0]["confidence"] == "medium"
    assert "vertical discontinuity" in plan["possible_issues"][0]["issue"].lower()


def test_visual_diagnostic_context_labels_checks_as_actions_not_faults():
    analysis = {
        "category": "SITE_PHOTO",
        "summary": "Display is active.",
        "visible_text": [],
        "devices": [],
        "observations": ["Display is active."],
        "possible_issues": [],
        "uncertainties": [],
    }

    context = build_visual_diagnostic_context(analysis)

    assert "VISIBLE FAULT STATUS: NO_OBVIOUS_VISIBLE_FAULT" in context
    assert "RECOMMENDED FIELD CHECKS:" in context
    assert "diagnostic actions, not claims that a fault exists" in context


def test_app_visual_rules_prioritize_field_diagnostics_over_low_value_details():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "What I can see → What looks wrong → What to check next." in app_source
    assert "If there is no visible issue, do not manufacture one." in app_source
    assert "icon labels, wallpaper details, or operating-system version" in app_source



def test_visual_completion_guard_rejects_partial_single_section_answer():
    answer = (
        "**What I can see:**\n\n"
        "- A large curved video display is visible. [DOC 1]"
    )
    question = (
        "What can you see in this image, what looks wrong, "
        "and what should I check next?"
    )

    assert visual_answer_is_complete(answer, question) is False


def test_visual_field_answer_contains_all_three_required_sections():
    analysis = {
        "category": "SITE_PHOTO",
        "summary": "A curved display is active.",
        "visible_text": [],
        "devices": [],
        "observations": [
            "A large curved display is active and showing a desktop.",
        ],
        "possible_issues": [],
        "uncertainties": [
            "Manufacturer and model are not readable.",
        ],
    }

    answer = build_visual_field_answer(
        analysis,
        citation_label="[DOC 1]",
    )

    assert "**What I can see:**" in answer
    assert "**What looks wrong:**" in answer
    assert "**What to check next:**" in answer
    assert "No obvious visual fault" in answer
    assert "[DOC 1]" in answer
    assert visual_answer_is_complete(
        answer,
        "What can you see in this image, what looks wrong, and what should I check next?",
    ) is True


def test_app_has_visual_completion_guard_after_grounded_verification():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "visual_answer_is_complete(answer, question)" in app_source
    assert "answer = build_visual_field_answer(" in app_source
