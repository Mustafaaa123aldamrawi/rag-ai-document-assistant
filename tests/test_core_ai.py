import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_ai import (build_recent_history, build_response_plan, build_router_prompt, classify_intent, preserve_follow_up_intent)


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
