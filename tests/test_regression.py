import ast
import re
from pathlib import Path

import pytest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def load_function_from_app(function_name):
    source = APP_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            module = ast.Module(body=[node], type_ignores=[])
            namespace = {}
            exec(compile(module, str(APP_FILE), "exec"), namespace)
            return namespace[function_name]

    raise AssertionError(
        f"Function {function_name} was not found in app.py"
    )


detect_pdf_content_type = load_function_from_app(
    "detect_pdf_content_type"
)


def make_pages(*texts):
    return [
        {
            "page_number": index,
            "source": "test.pdf",
            "text": text,
            "has_extractable_text": bool(text.strip()),
        }
        for index, text in enumerate(texts, start=1)
    ]


@pytest.mark.parametrize(
    "name,text",
    [
        (
            "AV-203.pdf",
            """
            AV-203
            ENCLOSED MEETING ROOM
            AV DEVICE LAYOUT
            AV CONTAINMENT LAYOUT
            AV ELEVATION
            SCALE 1:20
            DRAWING #
            """,
        ),
        (
            "AV-206.pdf",
            """
            AV-206
            WORK CAFE
            AV DEVICE LAYOUT
            AV CONTAINMENT LAYOUT
            AV ELEVATION
            AS SHOWN @ A1
            """,
        ),
        (
            "AV-209.pdf",
            """
            AV-209.1
            AV RACK ROOM
            AV DEVICE FLOOR PLAN
            AV INFRASTRUCTURE FLOOR PLAN
            DRAWING #
            SCALE 1:50
            """,
        ),
    ],
)
def test_known_av_drawings_are_detected_as_drawings(name, text):
    pages = make_pages(text)

    result = detect_pdf_content_type(
        pages,
        name,
    )

    assert result == "DRAWING"


@pytest.mark.parametrize(
    "name,text",
    [
        (
            "user_manual.pdf",
            """
            USER MANUAL
            TABLE OF CONTENTS
            IMPORTANT SAFETY INSTRUCTIONS
            WARRANTY
            SPECIFICATIONS
            """,
        ),
        (
            "installation_guide.pdf",
            """
            INSTALLATION GUIDE
            QUICK START GUIDE
            HARDWARE USER GUIDE
            IMPORTANT SAFETY INSTRUCTIONS
            """,
        ),
    ],
)
def test_normal_documents_stay_documents(name, text):
    pages = make_pages(text)

    result = detect_pdf_content_type(
        pages,
        name,
    )

    assert result == "DOCUMENT"


def test_generic_text_does_not_become_drawing():
    pages = make_pages(
        """
        Project meeting notes.
        The team reviewed progress and discussed next actions.
        No technical drawing is included.
        """
    )

    result = detect_pdf_content_type(
        pages,
        "meeting_notes.pdf",
    )

    assert result == "DOCUMENT"
    
decide_query_route = load_function_from_app(
    "decide_query_route"
)
should_run_drawing_vision = load_function_from_app(
    "should_run_drawing_vision"
)
normalize_equipment_quantities = load_function_from_app(
    "normalize_equipment_quantities"
)
extract_primary_drawing_number = load_function_from_app(
    "extract_primary_drawing_number"
)
extract_primary_drawing_number.__globals__["re"] = re
should_run_drawing_vision.__globals__["decide_query_route"] = decide_query_route

@pytest.mark.parametrize(
    "question,search_mode,has_document,content_type,document_scope_active,is_follow_up,expected",
    [
        (
            "What is the latest Cisco Room Bar firmware?",
            "Documents + Web",
            False,
            None,
            False,
            False,
            "WEB",
        ),
        (
            "What equipment is shown in this drawing?",
            "Documents + Web",
            True,
            "DRAWING",
            False,
            False,
            "DRAWING",
        ),
        (
            "What does this document say about installation?",
            "Documents + Web",
            True,
            "DOCUMENT",
            False,
            False,
            "DOCUMENT",
        ),
        (
            "What is the latest firmware for the device in this drawing?",
            "Documents + Web",
            True,
            "DRAWING",
            False,
            False,
            "HYBRID",
        ),
        (
            "شو الأجهزة الموجودة في هذا المخطط؟",
            "Documents + Web",
            True,
            "DRAWING",
            False,
            False,
            "DRAWING",
        ),
        (
            "شو آخر إصدار للجهاز الموجود في هذا المخطط؟",
            "Documents + Web",
            True,
            "DRAWING",
            False,
            False,
            "HYBRID",
        ),
        (
            "Explain acoustic echo cancellation",
            "Documents + Web",
            False,
            None,
            False,
            False,
            "GENERAL",
        ),
        (
            "What about its price?",
            "Documents + Web",
            True,
            "DOCUMENT",
            True,
            True,
            "HYBRID",
        ),
        (
            "Find the latest Shure MXA920 firmware",
            "Web Only",
            True,
            "DOCUMENT",
            False,
            False,
            "WEB",
        ),
        (
            "List the equipment",
            "Documents Only",
            True,
            "DRAWING",
            False,
            False,
            "DRAWING",
        ),
        (
            "Summarize the uploaded manual",
            "Documents Only",
            True,
            "DOCUMENT",
            False,
            False,
            "DOCUMENT",
        ),
    ],
)
def test_query_router(
    question,
    search_mode,
    has_document,
    content_type,
    document_scope_active,
    is_follow_up,
    expected,
):
    result = decide_query_route(
        question=question,
        search_mode=search_mode,
        has_document=has_document,
        content_type=content_type,
        document_scope_active=document_scope_active,
        is_follow_up=is_follow_up,
    )

    assert result == expected

    
def test_drawing_vision_does_not_run_without_question():
    result = should_run_drawing_vision(
        content_type="DRAWING",
        pending_question="",
        search_mode="Documents + Web",
        document_scope_active=False,
    )

    assert result is False


def test_drawing_vision_runs_for_drawing_question():
    result = should_run_drawing_vision(
        content_type="DRAWING",
        pending_question="What equipment is shown in this drawing?",
        search_mode="Documents + Web",
        document_scope_active=False,
    )

    assert result is True


def test_drawing_vision_runs_for_hybrid_question():
    result = should_run_drawing_vision(
        content_type="DRAWING",
        pending_question="What is the latest firmware for the device in this drawing?",
        search_mode="Documents + Web",
        document_scope_active=False,
    )

    assert result is True
def test_normalize_equipment_quantities():
    data = {
        "equipment": [
            {"name": "Display", "quantity": " 2 "},
            {"name": "Camera", "quantity": 1},
            {"name": "Speaker", "quantity": "multiple"},
        ]
    }

    result = normalize_equipment_quantities(data)

    assert result["equipment"][0]["quantity"] == 2
    assert result["equipment"][1]["quantity"] == 1
    assert result["equipment"][2]["quantity"] == "multiple"
    

def test_extract_primary_drawing_number():
    source_text = """
    PROJECT AV DRAWINGS
    AV-203
    AS SHOWN @ A1 AV-203
    """

    primary_number, normalized_numbers = extract_primary_drawing_number(
        source_text
    )

    assert primary_number == "AV-203"
    assert "AV-203" in normalized_numbers
    
