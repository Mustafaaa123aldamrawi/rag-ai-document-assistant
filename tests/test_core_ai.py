import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_ai import (build_grounded_verification_prompt, build_recent_history, build_response_plan, build_router_prompt, classify_intent, extract_citation_labels, preserve_follow_up_intent, should_verify_grounded_answer, unsupported_citation_labels, select_available_model, restore_source_technical_terms, is_safe_verifier_output)


def test_classifier_accepts_valid_label():
    assert classify_intent("Summarize the PDF", "", lambda _: "DOCUMENT") == "DOCUMENT"


def test_classifier_falls_back_safely():
    assert classify_intent("Hello", "", lambda _: "SOMETHING_ELSE") == "CASUAL"


def test_document_plan_uses_document_without_web():
    plan = build_response_plan(
        "DOCUMENT",
        search_mode="Documents + Web",
        has_document=True,
        is_follow_up=False,
    )
    assert plan.use_documents is True
    assert plan.use_web is False
    assert plan.verify_document_fidelity is True


def test_current_web_plan_can_combine_document_and_web():
    plan = build_response_plan(
        "WEB_CURRENT",
        search_mode="Documents + Web",
        has_document=True,
        is_follow_up=True,
    )
    assert plan.use_web is True
    assert plan.use_documents is True
    assert plan.preserve_conversation_context is True


def test_router_prompt_contains_current_question():
    prompt = build_router_prompt("What is the latest Q-SYS firmware?", "User: Hi")
    assert "What is the latest Q-SYS firmware?" in prompt
    assert "WEB_CURRENT" in prompt


def test_technical_plan_uses_documents_when_available():
    plan = build_response_plan(
        "TECHNICAL",
        search_mode="Documents + Web",
        has_document=True,
        is_follow_up=False,
    )
    assert plan.use_documents is True
    assert plan.use_web is False


def test_technical_plan_uses_web_when_no_document_is_available():
    plan = build_response_plan(
        "TECHNICAL",
        search_mode="Documents + Web",
        has_document=False,
        is_follow_up=False,
    )
    assert plan.use_documents is False
    assert plan.use_web is True


def test_build_recent_history_keeps_recent_turns():
    messages = [
        {"role": "user", "content": "Summarize the PDF"},
        {"role": "assistant", "content": "Summary"},
        {"role": "user", "content": "What about Room 2?"},
    ]
    history = build_recent_history(messages, limit=2)
    assert "Assistant: Summary" in history
    assert "User: What about Room 2?" in history
    assert "Summarize the PDF" not in history


def test_follow_up_inherits_document_intent_when_document_exists():
    assert preserve_follow_up_intent(
        "TECHNICAL",
        "DOCUMENT",
        is_follow_up=True,
        has_document=True,
    ) == "DOCUMENT"


def test_follow_up_does_not_override_explicit_writing_request():
    assert preserve_follow_up_intent(
        "WRITING",
        "DOCUMENT",
        is_follow_up=True,
        has_document=True,
    ) == "WRITING"


def test_follow_up_document_intent_degrades_without_document():
    assert preserve_follow_up_intent(
        "CASUAL",
        "DOCUMENT",
        is_follow_up=True,
        has_document=False,
    ) == "TECHNICAL"


def test_extract_citation_labels():
    assert extract_citation_labels("A [DOC 2] B [WEB 4]") == {"[DOC 2]", "[WEB 4]"}


def test_unsupported_citation_labels_detects_invented_source():
    assert unsupported_citation_labels(
        "Claim [DOC 1] other [WEB 9]",
        "[DOC 1] source text",
    ) == {"[WEB 9]"}


def test_grounded_answer_requires_verification():
    assert should_verify_grounded_answer(
        "Supported claim [DOC 1]",
        "[DOC 1] source",
        use_documents=True,
        use_web=False,
    ) is True


def test_casual_answer_skips_grounded_verification():
    assert should_verify_grounded_answer(
        "Hello!",
        "",
        use_documents=False,
        use_web=False,
    ) is False


def test_verification_prompt_prevents_requirement_condition_drift():
    prompt = build_grounded_verification_prompt(
        question="Summarize",
        context="[DOC 1] Customer shall provide network access.",
        answer="Network access is installed. [DOC 1]",
    )
    assert "Do not turn a source requirement into an observed site condition." in prompt
    assert "Customer shall provide network access." in prompt



def test_select_available_model_respects_preference_order():
    selected = select_available_model(
        ["large", "fast", "fallback"],
        {"fast", "fallback"},
    )
    assert selected == "fast"


def test_select_available_model_returns_none_when_unavailable():
    assert select_available_model(["large"], {"small"}) is None



def test_restore_source_technical_terms_repairs_av_drift():
    context = (
        "Hamad Tower. A new partition sensor shall be provided. "
        "The existing codec shall be handed over for E-waste disposal. "
        "Poly Studio G62 shall be the primary video conferencing platform."
    )
    answer = (
        "Hamd Tower uses a blade sensor. Equipment goes for electronic waste monitoring. "
        "Poly Studio G62 is the basic video communications platform."
    )
    fixed = restore_source_technical_terms(answer, context)
    assert "Hamad Tower" in fixed
    assert "partition sensor" in fixed
    assert "E-waste disposal" in fixed
    assert "primary video conferencing platform" in fixed
    assert "blade sensor" not in fixed


def test_restore_source_technical_terms_does_not_inject_absent_terms():
    fixed = restore_source_technical_terms(
        "The wall sensor is visible.",
        "The room contains a generic sensor.",
    )
    assert "wall sensor" in fixed
    assert "partition sensor" not in fixed



def test_verifier_output_rejects_prompt_echo():
    candidate = (
        "Review the answer against the exact cited source content below.\n"
        "SOURCE CONTENT: [DOC 1] raw source"
    )
    assert is_safe_verifier_output(candidate, "Room-2 uses a new microphone [DOC 4].") is False


def test_verifier_output_rejects_large_source_dump():
    original = "Room-2 uses a new microphone [DOC 4]."
    candidate = "\n".join(
        f"[DOC {i}] source text {i}" for i in range(1, 10)
    )
    assert is_safe_verifier_output(candidate, original) is False


def test_verifier_output_accepts_clean_corrected_answer():
    candidate = (
        "Room-2 is equipped with a new ceiling array microphone for Audio fill [DOC 4]."
    )
    assert is_safe_verifier_output(
        candidate,
        "Room-2 has a microphone [DOC 4].",
    ) is True
