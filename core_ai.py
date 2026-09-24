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


def build_recent_history(messages, limit: int = 6) -> str:
    """Build a compact recent conversation transcript for routing and follow-ups."""
    if not messages:
        return ""

    selected = messages[-limit:]
    lines = []

    for message in selected:
        role = message.get("role", "user")
        content = str(message.get("content", "")).strip()
        if not content:
            continue

        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")

    return "\n".join(lines)


def preserve_follow_up_intent(
    current_intent: Intent,
    previous_intent: Intent | None,
    *,
    is_follow_up: bool,
    has_document: bool,
) -> Intent:
    """Preserve conversational continuity only when the current turn is ambiguous."""
    if not is_follow_up or not previous_intent:
        return current_intent

    if current_intent in {"WRITING", "TRANSLATION", "WEB_CURRENT"}:
        return current_intent

    if current_intent == "CASUAL" and previous_intent in {
        "DOCUMENT",
        "TECHNICAL",
        "WEB_CURRENT",
    }:
        if previous_intent == "DOCUMENT" and not has_document:
            return "TECHNICAL"
        return previous_intent

    if (
        current_intent == "TECHNICAL"
        and previous_intent == "DOCUMENT"
        and has_document
    ):
        return "DOCUMENT"

    return current_intent


def extract_citation_labels(text: str) -> set[str]:
    import re
    return {
        f"[{source} {number}]"
        for source, number in re.findall(r"\[(DOC|WEB)\s+(\d+)\]", text or "")
    }


def unsupported_citation_labels(answer: str, context: str) -> set[str]:
    answer_labels = extract_citation_labels(answer)
    context_labels = extract_citation_labels(context)
    return answer_labels - context_labels


def should_verify_grounded_answer(
    answer: str,
    context: str,
    *,
    use_documents: bool,
    use_web: bool,
) -> bool:
    if not (answer or "").strip() or str(answer).startswith("AI model error:"):
        return False
    if not (use_documents or use_web):
        return False
    return bool((context or "").strip())


def build_grounded_verification_prompt(
    *,
    question: str,
    context: str,
    answer: str,
) -> str:
    return f"""
Verify the CURRENT ANSWER strictly against the AVAILABLE CONTEXT.

USER QUESTION:
{question}

AVAILABLE CONTEXT:
{context}

CURRENT ANSWER:
{answer}

Verification rules:
- Preserve the user's requested language and concise professional style.
- Keep only factual claims that are supported by the AVAILABLE CONTEXT.
- Preserve exact manufacturers, product names, model numbers, room names, project names, quantities, lifecycle actions, and technical terminology when they appear in the context.
- Never upgrade, rename, infer, or substitute one device category for another.
- Use only [DOC X] and [WEB X] citation labels that actually occur in the AVAILABLE CONTEXT.
- Remove unsupported citation labels.
- Every factual bullet or factual sentence derived from the context must keep an appropriate supporting citation.
- If a claim is only partially supported, shorten it to the supported portion.
- Do not add facts, recommendations, examples, products, standards, quantities, dates, or conclusions that are not already supported.
- Do not turn a source requirement into an observed site condition.
- Do not turn an existing-condition statement into a design requirement.
- Preserve uncertainty when the source is uncertain.
- If the answer is already fully supported, preserve it as closely as possible.
- Return only the verified final answer.

VERIFIED ANSWER:
""".strip()



def select_available_model(
    preferred_models,
    available_model_ids,
):
    available = set(available_model_ids or [])
    for model_id in preferred_models or []:
        if model_id in available:
            return model_id
    return None
