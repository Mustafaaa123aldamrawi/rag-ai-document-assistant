import ast
import re
import json
from pathlib import Path

import pytest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def load_function_from_app(function_name):
    source = APP_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            module = ast.Module(body=[node], type_ignores=[])
            namespace = {
                "observe": lambda *args, **kwargs: (
                    lambda func: func
                ),
            }
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
detect_follow_up_question = load_function_from_app(
    "detect_follow_up_question"
)
should_show_document_not_found = load_function_from_app(
    "should_show_document_not_found"
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
validate_structured_drawing_number = load_function_from_app(
    "validate_structured_drawing_number"
)
filter_installation_notes = load_function_from_app(
    "filter_installation_notes"
)
deduplicate_references = load_function_from_app(
    "deduplicate_references"
)
move_reference_notes = load_function_from_app(
    "move_reference_notes"
)
promote_confirmed_installation_notes = load_function_from_app(
    "promote_confirmed_installation_notes"
)
deduplicate_installation_notes = load_function_from_app(
    "deduplicate_installation_notes"
)
build_drawing_cache_key = load_function_from_app(
    "build_drawing_cache_key"
)
build_drawing_analysis_page = load_function_from_app(
    "build_drawing_analysis_page"
)
get_drawing_analysis_pages = load_function_from_app(
    "get_drawing_analysis_pages"
)
is_generic_room_label = load_function_from_app(
    "is_generic_room_label"
)
is_ambiguous_equipment_annotation = load_function_from_app(
    "is_ambiguous_equipment_annotation"
)
simplify_composite_equipment_name = load_function_from_app(
    "simplify_composite_equipment_name"
)
extract_primary_drawing_number.__globals__["re"] = re
validate_structured_drawing_number.__globals__["re"] = re
deduplicate_references.__globals__["re"] = re
deduplicate_installation_notes.__globals__["re"] = re
build_drawing_analysis_page.__globals__["json"] = json
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


def test_validate_structured_drawing_number():
    data = {
        "drawing_number": "AV-999"
    }
    uncertainty_notes = []

    result = validate_structured_drawing_number(
        structured_drawing_data=data,
        primary_drawing_number=None,
        normalized_source_numbers=["AV-203"],
        uncertainty_notes=uncertainty_notes,
    )

    assert result["drawing_number"] is None
    assert uncertainty_notes == [
        "Rejected unsupported drawing number: AV-999"
    ]
    
def test_filter_installation_notes():
    installation_notes = [
        "Mount display at 1200 mm AFF",
        "Dimension: 1200 mm",
        "Provide backing for display",
        "Reference tag AV-203",
        "N/A",
    ]

    uncertainty_notes = []

    result = filter_installation_notes(
        installation_notes,
        uncertainty_notes,
    )

    assert result == [
        "Provide backing for display",
        "N/A",
    ]
    
    assert "Mount display at 1200 mm AFF" in uncertainty_notes
    assert "Dimension: 1200 mm" in uncertainty_notes
    assert "Reference tag AV-203" in uncertainty_notes

def test_deduplicate_references():
    references = [
        "AV-203",
        "  AV-203  ",
        "av-203",
        "AV-206",
        {"type": "drawing", "value": "AV-209"},
    ]

    result = deduplicate_references(references)

    assert result == [
        "AV-203",
        "AV-206",
        {"type": "drawing", "value": "AV-209"},
    ]

def test_move_reference_notes():
    filtered_installation_notes = [
        "Provide backing for display",
        "Project: Riyadh HQ",
        "Mount camera above display",
        "Revision: A",
    ]

    references = []
    reference_patterns = [
        "project:",
        "revision:",
    ]

    result = move_reference_notes(
        filtered_installation_notes,
        references,
        reference_patterns,
    )

    assert result == [
        "Provide backing for display",
        "Mount camera above display",
    ]

    assert references == [
        "Project: Riyadh HQ",
        "Revision: A",
    ]
    
def test_promote_confirmed_installation_notes():
    data = {
        "installation_notes": [
            "Mount display on wall"
        ]
    }

    uncertainty_notes = [
        "Provide backing for display",
        "Unknown room label",
    ]

    cleaned_vision_answer = """
    Camera location confirmed.
    Backing to withstand display load.
    """

    confirmed_installation_patterns = [
        "backing to withstand",
        "provide backing",
    ]

    remaining_uncertainty_notes = promote_confirmed_installation_notes(
        structured_drawing_data=data,
        uncertainty_notes=uncertainty_notes,
        cleaned_vision_answer=cleaned_vision_answer,
        confirmed_installation_patterns=confirmed_installation_patterns,
    )

    assert data["installation_notes"] == [
        "Mount display on wall",
        "Provide backing for display",
        "Backing to withstand display load.",
    ]

    assert remaining_uncertainty_notes == [
        "Unknown room label"
    ]

def test_deduplicate_installation_notes():
    installation_notes = [
        "Provide backing for display",
        "- Provide backing for display",
        "(1) Provide backing for display",
        "Mount camera above display",
    ]

    result = deduplicate_installation_notes(
        installation_notes
    )

    assert result == [
        "Provide backing for display",
        "Mount camera above display",
    ]

def test_build_drawing_cache_key():
    class FakeUploadedFile:
        def __init__(self, name, size):
            self.name = name
            self.size = size

    drawing_a = FakeUploadedFile(
        "AV-203.pdf",
        12345,
    )

    drawing_a_copy = FakeUploadedFile(
        "AV-203.pdf",
        12345,
    )

    drawing_b = FakeUploadedFile(
        "AV-206.pdf",
        54321,
    )

    key_a = build_drawing_cache_key(drawing_a)
    key_a_copy = build_drawing_cache_key(drawing_a_copy)
    key_b = build_drawing_cache_key(drawing_b)

    assert key_a == "AV-203.pdf:12345"
    assert key_a == key_a_copy
    assert key_a != key_b

def test_build_drawing_analysis_page():
    structured_drawing_data = {
        "drawing_number": "AV-203",
        "equipment": [
            {
                "name": "Display",
                "quantity": 2,
            }
        ],
    }

    result = build_drawing_analysis_page(
        structured_drawing_data,
        "AV-203.pdf",
    )

    assert result["page_number"] == 1
    assert result["source"] == "AV-203.pdf"
    assert result["content_type"] == "DRAWING"
    assert result["is_drawing_analysis"] is True
    assert result["has_extractable_text"] is True
    assert '"drawing_number": "AV-203"' in result["text"]
    assert '"name": "Display"' in result["text"]

def test_build_drawing_analysis_page_returns_none_without_data():
    result = build_drawing_analysis_page(
        None,
        "AV-203.pdf",
    )

    assert result is None

def test_get_drawing_analysis_pages():
    document_pages = [
        {
            "source": "AV-203.pdf",
            "text": "Normal extracted PDF text",
            "is_drawing_analysis": False,
        },
        {
            "source": "AV-203.pdf",
            "text": '{"drawing_number": "AV-203", "quantity": 2}',
            "is_drawing_analysis": True,
        },
        {
            "source": "AV-206.pdf",
            "text": "",
            "is_drawing_analysis": True,
        },
    ]

    result = get_drawing_analysis_pages(document_pages)

    assert len(result) == 1
    assert result[0]["is_drawing_analysis"] is True
    assert '"quantity": 2' in result[0]["text"]

@pytest.mark.parametrize(
    "question,expected",
    [
        ("What about its quantities?", True),
        ("And what are the quantities?", True),
("طيب شو الكميات؟", True),
        ("What are the quantities?", False),
        ("What equipment is shown in this drawing?", False),
    ],
)
def test_detect_follow_up_question(question, expected):
    assert detect_follow_up_question(question) is expected

@pytest.mark.parametrize(
    "room_area,expected",
    [
        ("AREA", True),
        ("VIEW", True),
        ("ENCLOSED HUDDLE AREA", False),
        ("BOARD ROOM", False),
    ],
)
def test_is_generic_room_label(room_area, expected):
    assert is_generic_room_label(room_area) is expected

@pytest.mark.parametrize(
    "equipment_item,expected",
    [
        (
            {
                "name": "Speaker Icon",
                "manufacturer": None,
                "model": None,
                "confidence": "medium",
            },
            True,
        ),
        (
            {
                "name": "Label/Floor Box N 1",
                "manufacturer": None,
                "model": None,
                "confidence": "low",
            },
            True,
        ),
        (
            {
                "name": "JBL Ceiling Speaker",
                "manufacturer": "JBL",
                "model": "Control 26CT",
                "confidence": "high",
            },
            False,
        ),
        (
            {
                "name": "Speaker Icon",
                "manufacturer": None,
                "model": None,
                "confidence": "high",
            },
            False,
        ),
    ],
)
def test_is_ambiguous_equipment_annotation(equipment_item, expected):
    assert is_ambiguous_equipment_annotation(equipment_item) is expected

@pytest.mark.parametrize(
    "equipment_item,expected_name",
    [
        (
            {
                "name": 'SAMSUNG QMC 55" DISPLAY MTM1U WALL MOUNT WITH FCAV1U',
                "manufacturer": "Samsung",
                "model": 'QMC 55" DISPLAY MTM1U',
            },
            'SAMSUNG QMC 55" DISPLAY MTM1U',
        ),
        (
            {
                "name": "CISCO VIDEO-BAR CS-BAR-T-K9 WITH WALL MOUNT",
                "manufacturer": "Cisco",
                "model": "CS-BAR-T-K9",
            },
            "CISCO VIDEO-BAR CS-BAR-T-K9",
        ),
        (
            {
                "name": "SURGEX SX-DPP-102I",
                "manufacturer": "Surgex",
                "model": "SX-DPP-102I",
            },
            "SURGEX SX-DPP-102I",
        ),
        (
            {
                "name": "CHIEF MTM1U WALL MOUNT",
                "manufacturer": "Chief",
                "model": "MTM1U",
            },
            "CHIEF MTM1U WALL MOUNT",
        ),
    ],
)

def test_simplify_composite_equipment_name(
    equipment_item,
    expected_name,
):
    result = simplify_composite_equipment_name(equipment_item)

    assert result["name"] == expected_name

def test_not_found_guard_does_not_stop_when_structured_drawing_context_exists():
    assert should_show_document_not_found(
        relevant_documents=[],
        is_summary_question=False,
        search_mode="Documents Only",
        is_casual_chat=False,
        has_additional_context=True,
    ) is False


def test_not_found_guard_stops_when_no_document_evidence_exists():
    assert should_show_document_not_found(
        relevant_documents=[],
        is_summary_question=False,
        search_mode="Documents Only",
        is_casual_chat=False,
        has_additional_context=False,
    ) is True
