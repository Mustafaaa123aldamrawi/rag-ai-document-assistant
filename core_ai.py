from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

Intent = Literal["CASUAL", "WRITING", "TRANSLATION", "TECHNICAL", "DOCUMENT", "WEB_CURRENT"]

ALLOWED_INTENTS = {
    "CASUAL",
    "WRITING",
    "TRANSLATION",
    "TECHNICAL",
    "DOCUMENT",
    "WEB_CURRENT",
}

@dataclass(frozen=True)
class ResponsePlan:
    intent: Intent
    use_documents: bool
    use_web: bool
    preserve_conversation_context: bool
    verify_document_fidelity: bool


def build_router_prompt(question: str, history: str = "") -> str:
    return f"""
Classify the user's CURRENT MESSAGE into exactly ONE intent.

Allowed intents:
CASUAL
WRITING
TRANSLATION
TECHNICAL
DOCUMENT
WEB_CURRENT

Definitions:
- CASUAL: normal conversation, general advice, or everyday help that does not require external research.
- WRITING: create, rewrite, polish, format, or reply to written content.
- TRANSLATION: explicitly translate text from one language to another.
- TECHNICAL: AV/UC, engineering, product, troubleshooting, design, installation, configuration, or professional-domain questions that do not require current web information.
- DOCUMENT: explicitly asks for information from, about, or based on uploaded documents.
- WEB_CURRENT: explicitly needs current, latest, changing, externally verified, or web-researched information.

Routing rules:
- Classify by the user's actual intent, not keywords alone.
- Technical product questions are TECHNICAL unless current/latest/web verification is explicitly needed.
- Writing requests remain WRITING even when the subject is technical.
- Explicit translation requests are TRANSLATION.
- Explicit requests based on uploaded files are DOCUMENT.
- Use recent conversation only to resolve short follow-ups and references.
- A follow-up should preserve the immediately relevant intent when appropriate.
- Return exactly one label and nothing else.

Recent conversation:
{history}

Current message:
{question}
""".strip()


def classify_intent(
    question: str,
    history: str,
    llm_call: Callable[[str], str],
) -> Intent:
    raw = (llm_call(build_router_prompt(question, history)) or "").strip().upper()
    if raw in ALLOWED_INTENTS:
        return raw  # type: ignore[return-value]
    return "CASUAL"


def build_response_plan(
    intent: Intent,
    *,
    search_mode: str,
    has_document: bool,
    is_follow_up: bool,
) -> ResponsePlan:
    use_documents = intent == "DOCUMENT" and has_document
    use_web = intent == "WEB_CURRENT"

    if search_mode == "Web Only":
        use_documents = False
        use_web = intent not in {"CASUAL", "WRITING", "TRANSLATION"}

    elif search_mode == "Documents Only":
        use_web = False
        use_documents = has_document and intent in {"DOCUMENT", "TECHNICAL"}

    elif search_mode == "Documents + Web":
        if intent == "DOCUMENT":
            use_documents = has_document
            use_web = False
        elif intent == "WEB_CURRENT":
            use_web = True
            use_documents = has_document
        elif intent == "TECHNICAL":
            use_documents = has_document
            use_web = not has_document

    return ResponsePlan(
        intent=intent,
        use_documents=use_documents,
        use_web=use_web,
        preserve_conversation_context=is_follow_up,
        verify_document_fidelity=use_documents,
    )
