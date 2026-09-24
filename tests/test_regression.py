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
get_follow_up_state = load_function_from_app(
    "get_follow_up_state"
)
get_follow_up_state.__globals__["detect_follow_up_question"] = (
    detect_follow_up_question
)
get_document_retrieval_k = load_function_from_app(
    "get_document_retrieval_k"
)
select_document_overview_pages = load_function_from_app(
    "select_document_overview_pages"
)
select_relevant_documents = load_function_from_app(
    "select_relevant_documents"
)
should_show_document_not_found = load_function_from_app(
    "should_show_document_not_found"
)
should_run_drawing_vision = load_function_from_app(
    "should_run_drawing_vision"
)
should_run_drawing_vision.__globals__["decide_query_route"] = (
    decide_query_route
)
should_run_drawing_vision.__globals__["get_follow_up_state"] = (
    get_follow_up_state
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
build_scope_of_work_context = load_function_from_app(
    "build_scope_of_work_context"
)
build_site_survey_blueprint_prompt = load_function_from_app(
    "build_site_survey_blueprint_prompt"
)
build_professional_site_survey_data = load_function_from_app(
    "build_professional_site_survey_data"
)
build_document_overview_instruction = load_function_from_app(
    "build_document_overview_instruction"
)
build_document_overview_fidelity_review_prompt = load_function_from_app(
    "build_document_overview_fidelity_review_prompt"
)
build_extractive_document_overview = load_function_from_app(
    "build_extractive_document_overview"
)
clean_extractive_overview_sentence = load_function_from_app(
    "clean_extractive_overview_sentence"
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
is_document_overview_question = load_function_from_app(
    "is_document_overview_question"
)
simplify_composite_equipment_name = load_function_from_app(
    "simplify_composite_equipment_name"
)
merge_split_equipment_items = load_function_from_app(
    "merge_split_equipment_items"
)
classify_drawing_fact_question = load_function_from_app(
    "classify_drawing_fact_question"
)

format_equipment_item_for_answer = load_function_from_app(
    "format_equipment_item_for_answer"
)
generate_deterministic_drawing_answer = load_function_from_app(
    "generate_deterministic_drawing_answer"
)
generate_site_survey_blueprint = load_function_from_app(
    "generate_site_survey_blueprint"
)
get_structured_drawing_data_from_pages = load_function_from_app(
    "get_structured_drawing_data_from_pages"
)
generate_site_survey_blueprint.__globals__[
    "build_site_survey_blueprint_prompt"
] = build_site_survey_blueprint_prompt

generate_site_survey_blueprint.__globals__[
    "json"
] = json
build_document_overview_instruction.__globals__[
    "is_document_overview_question"
] = is_document_overview_question
build_extractive_document_overview.__globals__["re"] = re
build_extractive_document_overview.__globals__[
    "clean_extractive_overview_sentence"
] = clean_extractive_overview_sentence
clean_extractive_overview_sentence.__globals__["re"] = re
get_document_retrieval_k.__globals__[
    "is_document_overview_question"
] = is_document_overview_question
extract_primary_drawing_number.__globals__["re"] = re
validate_structured_drawing_number.__globals__["re"] = re
deduplicate_references.__globals__["re"] = re
deduplicate_installation_notes.__globals__["re"] = re
build_drawing_analysis_page.__globals__["json"] = json
get_structured_drawing_data_from_pages.__globals__["json"] = json
should_run_drawing_vision.__globals__["decide_query_route"] = decide_query_route
decide_query_route.__globals__[
    "is_document_overview_question"
] = is_document_overview_question
generate_deterministic_drawing_answer.__globals__[
    "classify_drawing_fact_question"
] = classify_drawing_fact_question

generate_deterministic_drawing_answer.__globals__[
    "format_equipment_item_for_answer"
] = format_equipment_item_for_answer

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

def test_merge_split_equipment_items_merges_identity_and_description():
    equipment_items = [
        {
            "name": "PANDUIT",
            "manufacturer": "PANDUIT",
            "model": "XG64512WS0001",
            "quantity": 2,
            "confidence": "high",
        },
        {
            "name": "45U HIGH AV RACK",
            "manufacturer": None,
            "model": "45U HIGH AV RACK",
            "quantity": None,
            "confidence": "high",
        },
    ]

    result = merge_split_equipment_items(equipment_items)

    assert len(result) == 1
    assert result[0]["name"] == "45U HIGH AV RACK"
    assert result[0]["manufacturer"] == "PANDUIT"
    assert result[0]["model"] == "XG64512WS0001"
    assert result[0]["quantity"] == 2


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

def test_follow_up_detection_is_consistent_for_explicit_source_question():
    question = "What equipment is shown in this drawing?"

    assert detect_follow_up_question(question) is False


def test_follow_up_detection_is_consistent_for_real_follow_up():
    question = "What about its quantities?"

    assert detect_follow_up_question(question) is True

@pytest.mark.parametrize(
    "question,expected",
    [
        ("What equipment is shown in this drawing?", False),
        ("What is the drawing number and title?", False),
        ("What about its quantities?", True),
        ("And what are the quantities?", True),
        ("طيب شو الكميات؟", True),
    ],
)
def test_get_follow_up_state(question, expected):
    assert get_follow_up_state(question) is expected

def test_format_equipment_item_preserves_exact_identity():
    item = {
        "name": "45U HIGH AV RACK",
        "manufacturer": "PANDUIT",
        "model": "XG64512WS0001",
        "quantity": 2,
    }

    result = format_equipment_item_for_answer(item)

    assert "45U HIGH AV RACK" in result
    assert "PANDUIT" in result
    assert "XG64512WS0001" in result
    lowered = result.lower()
    assert "video game" not in lowered
    assert "shelf" not in lowered
    assert "45 units" not in lowered
    assert "units per shelf" not in lowered


def test_format_equipment_item_does_not_invent_missing_fields():
    item = {
        "name": "TOUCH PANEL",
        "manufacturer": None,
        "model": None,
        "quantity": None,
    }

    result = format_equipment_item_for_answer(item)

    assert "TOUCH PANEL" in result
    assert "Manufacturer:" not in result
    assert "Model:" not in result
    assert "Quantity:" not in result


def test_quantity_follow_up_is_deterministic_lookup():
    result = classify_drawing_fact_question(
        "What about its quantities?"
    )

    assert result == "quantity"


def test_explanation_question_stays_llm_driven():
    result = classify_drawing_fact_question(
        "Explain how this rack should be installed"
    )

    assert result is None


def test_generate_deterministic_drawing_answer_preserves_equipment_identity():
    structured_data = {
        "drawing_number": "AV-209.1",
        "drawing_title": "AV RACK ROOM",
        "room_areas": ["AV RACK ROOM"],
        "equipment": [
            {
                "name": "45U HIGH AV RACK",
                "manufacturer": "PANDUIT",
                "model": "XG64512WS0001",
                "quantity": 2,
            }
        ],
        "installation_notes": [],
    }

    result = generate_deterministic_drawing_answer(
        "What equipment is shown in this drawing?",
        structured_data,
        "[DOC 1]",
    )

    assert "45U HIGH AV RACK" in result
    assert "PANDUIT" in result
    assert "XG64512WS0001" in result
    assert "Quantity: 2" in result
    assert "[DOC 1]" in result

    lowered = result.lower()
    assert "video game" not in lowered
    assert "shelf" not in lowered
    assert "45 units" not in lowered


def test_generate_deterministic_quantity_answer():
    structured_data = {
        "equipment": [
            {
                "name": "45U HIGH AV RACK",
                "manufacturer": "PANDUIT",
                "model": "XG64512WS0001",
                "quantity": 2,
            }
        ]
    }

    result = generate_deterministic_drawing_answer(
        "What about its quantities?",
        structured_data,
        "[DOC 1]",
    )

    assert result == "- 45U HIGH AV RACK | Quantity: 2 [DOC 1]"


def test_generate_deterministic_answer_does_not_invent_missing_quantity():
    structured_data = {
        "equipment": [
            {
                "name": "TOUCH PANEL",
                "manufacturer": "CRESTRON",
                "model": "TS-1070",
                "quantity": None,
            }
        ]
    }

    result = generate_deterministic_drawing_answer(
        "What are the quantities?",
        structured_data,
        "[DOC 1]",
    )

    assert "TOUCH PANEL" in result
    assert "Quantity: unspecified" in result


def test_generate_deterministic_answer_returns_none_for_explanation():
    structured_data = {
        "equipment": [
            {
                "name": "45U HIGH AV RACK",
                "manufacturer": "PANDUIT",
                "model": "XG64512WS0001",
                "quantity": 2,
            }
        ]
    }

    result = generate_deterministic_drawing_answer(
        "Explain how this rack should be installed",
        structured_data,
        "[DOC 1]",
    )

    assert result is None


def test_get_structured_drawing_data_from_pages():
    document_pages = [
        {
            "page_number": 1,
            "source": "AV-209.pdf",
            "text": '{"drawing_number":"AV-209.1","drawing_title":"AV RACK ROOM"}',
            "content_type": "DRAWING",
            "is_drawing_analysis": True,
        },
        {
            "page_number": 2,
            "source": "AV-209.pdf",
            "text": "normal extracted drawing text",
            "content_type": "DRAWING",
            "is_drawing_analysis": False,
        },
    ]

    result = get_structured_drawing_data_from_pages(document_pages)

    assert len(result) == 1
    assert result[0]["data"]["drawing_number"] == "AV-209.1"
    assert result[0]["data"]["drawing_title"] == "AV RACK ROOM"
    assert result[0]["source"] == "AV-209.pdf"
    assert result[0]["page_number"] == 1

def test_merge_split_equipment_items_handles_name_with_manufacturer_and_model():
    items = [
        {
            "name": "PANDUIT XG64512WS0001",
            "manufacturer": "PANDUIT",
            "model": "XG64512WS0001",
            "quantity": 2,
            "confidence": "high",
        },
        {
            "name": "45U HIGH AV RACK",
            "manufacturer": None,
            "model": None,
            "quantity": None,
            "confidence": "high",
        },
    ]

    result = merge_split_equipment_items(items)

    assert len(result) == 1
    assert result[0]["name"] == "45U HIGH AV RACK"
    assert result[0]["manufacturer"] == "PANDUIT"
    assert result[0]["model"] == "XG64512WS0001"
    assert result[0]["quantity"] == 2

def test_is_ambiguous_equipment_annotation_filters_standalone_current_rating():
    item = {
        "name": "32A",
        "manufacturer": None,
        "model": None,
        "confidence": "medium",
    }

    assert is_ambiguous_equipment_annotation(item) is True


def test_is_ambiguous_equipment_annotation_filters_standalone_voltage_rating():
    item = {
        "name": "230V",
        "manufacturer": None,
        "model": None,
        "confidence": "high",
    }

    assert is_ambiguous_equipment_annotation(item) is True

def test_simplify_composite_equipment_name_repairs_swapped_identity_fields():
    item = {
        "name": "PANDUIT XG64512WS0001",
        "manufacturer": None,
        "model": "45U HIGH AV RACK",
        "quantity": 2,
        "confidence": "high",
    }

    result = simplify_composite_equipment_name(item)

    assert result["name"] == "45U HIGH AV RACK"
    assert result["manufacturer"] == "PANDUIT"
    assert result["model"] == "XG64512WS0001"
    assert result["quantity"] == 2

def test_is_ambiguous_equipment_annotation_filters_descriptive_electrical_callout():
    item = {
        "name": "32A power outlet rating",
        "manufacturer": None,
        "model": None,
        "confidence": "low",
    }

    assert is_ambiguous_equipment_annotation(item) is True

def test_build_scope_of_work_context_uses_original_pages_only():
    document_pages = [
        {
            "page_number": 1,
            "source": "Scope_of_Work.pdf",
            "text": "Install AV equipment in Meeting Room A.",
            "is_drawing_analysis": False,
        },
        {
            "page_number": 2,
            "source": "Scope_of_Work.pdf",
            "text": "Verify rack power, network, and cable routes.",
            "is_drawing_analysis": False,
        },
        {
            "page_number": 1,
            "source": "Scope_of_Work.pdf",
            "text": '{"drawing_number":"AV-101"}',
            "is_drawing_analysis": True,
        },
    ]

    result = build_scope_of_work_context(document_pages)

    assert "Scope_of_Work.pdf - Page 1" in result
    assert "Install AV equipment in Meeting Room A." in result
    assert "Scope_of_Work.pdf - Page 2" in result
    assert "Verify rack power, network, and cable routes." in result
    assert '"drawing_number":"AV-101"' not in result
    
def test_build_site_survey_blueprint_prompt_is_compact_and_grounded():
    scope_context = """
    Project: Mastercard Riyadh
    Location: 3rd Floor - Hamad Tower
    Existing equipment: 2x Samsung QB65H displays
    New equipment: Poly Studio G62
    Divisible meeting room with partition sensor
    """

    prompt = build_site_survey_blueprint_prompt(scope_context)

    assert prompt is not None
    assert "Mastercard Riyadh" in prompt
    assert "Samsung QB65H" in prompt
    assert "Poly Studio G62" in prompt
    assert '"divisible_room": false' in prompt
    assert '"partition_sensor": false' in prompt

    assert "Return ONLY valid JSON" in prompt
    assert "Do not invent" in prompt

def test_generate_site_survey_blueprint_parses_valid_json():
    def fake_llm(prompt, temperature=0.1):
        return """
        {
          "project": {
            "name": "Mastercard Riyadh",
            "client": "Mastercard",
            "location": "3rd Floor - Hamad Tower",
            "rooms": ["Divisible Meeting Rooms"],
            "drawing_references": []
          },
          "existing_equipment": [],
          "new_equipment": [],
          "project_features": {
            "divisible_room": true,
            "partition_sensor": true,
            "rack_work": false,
            "ceiling_work": false,
            "dante": false,
            "network_work": false,
            "power_work": false,
            "cable_route_work": false,
            "equipment_relocation": false,
            "equipment_removal": false
          },
          "critical_requirements": [],
          "connections_to_verify": [],
          "cable_routes_to_verify": [],
          "relocations": [],
          "removals": [],
          "design_intent": []
        }
        """

    generate_site_survey_blueprint.__globals__[
        "call_conversation_llm"
    ] = fake_llm

    result = generate_site_survey_blueprint(
        "Mastercard Riyadh divisible meeting room with partition sensor."
    )

    assert result["project"]["name"] == "Mastercard Riyadh"
    assert result["project_features"]["divisible_room"] is True
    assert result["project_features"]["partition_sensor"] is True

def test_build_professional_site_survey_data_builds_dynamic_structure():
    blueprint = {
        "project": {
            "name": "Mastercard Riyadh",
            "client": "Mastercard",
            "location": "3rd Floor - Hamad Tower",
            "rooms": ["Divisible Meeting Rooms"],
            "drawing_references": [
                "DE Layout",
                "DE Schematics",
            ],
        },
        "existing_equipment": [
            {
                "device": "Display",
                "quantity": 2,
                "manufacturer": "Samsung",
                "model": "QB65H",
                "location": "Room 1",
            }
        ],
        "new_equipment": [
            {
                "device": "Codec",
                "quantity": 1,
                "manufacturer": "Poly",
                "model": "Studio G62",
                "location": "AV Rack",
            }
        ],
        "project_features": {
            "divisible_room": True,
            "partition_sensor": True,
            "rack_work": True,
            "ceiling_work": True,
            "dante": True,
            "network_work": True,
            "power_work": True,
            "cable_route_work": True,
            "equipment_relocation": True,
            "equipment_removal": True,
        },
        "critical_requirements": [
            "Verify partition sensor dry contact availability"
        ],
        "connections_to_verify": [
            "Poly Studio G62 to network",
            "Poly Studio G62 to displays",
        ],
        "cable_routes_to_verify": [
            "AV rack to ceiling microphone"
        ],
        "relocations": [],
        "removals": [],
        "design_intent": [],
    }

    result = build_professional_site_survey_data(
        blueprint
    )

    assert result is not None

    assert (
        result["document_meta"]["title"]
        == "Mastercard Riyadh Site Survey Checklist"
    )

    assert (
        result["project_info"]["client"]
        == "Mastercard"
    )

    assert (
        result["existing_equipment_inventory"][0]["model"]
        == "QB65H"
    )

    priority_names = [
        item["priority_item"]
        for item in result["survey_priorities"]
    ]

    assert "Ceiling coordination" in priority_names
    assert "Partition sensor / interface" in priority_names
    assert "Cable routes" in priority_names
    assert "AV rack capacity" in priority_names

    assert len(result["connection_matrix"]) == 2
    assert len(result["cable_routes"]) == 1

    assert len(result["photo_register"]) == 24
    assert len(result["deviations_risks_actions"]) == 8

    assert len(result["final_survey_outcome"]) == 6
    assert len(result["sign_off"]) == 3

def test_scope_of_work_document_with_drawing_terms_stays_document():
    pages = [
        {
            "text": """
            Mastercard Riyadh Scope of Work

            Project Considerations
            Statement of Work
            Responsibilities and installation requirements.

            Refer to AV DEVICE FLOOR PLAN.
            Refer to AV INFRASTRUCTURE FLOOR PLAN.
            DRAWING NO.
            SCALE 1:50
            GENERAL ARRANGEMENT

            The scope defines existing equipment, proposed equipment,
            rack work, cabling, power, network, partition sensor,
            testing and commissioning requirements.

            Refer to drawings and specifications for coordination.
            """,
            "has_extractable_text": True,
        }
    ]

    result = detect_pdf_content_type(
        pages,
        "Mastercard Riyadh_Scope of Work11.pdf",
    )

    assert result == "DOCUMENT"

@pytest.mark.parametrize(
    "question, expected",
    [
        ("Can you tell me what the PDF is about?", True),
        ("Summarize this document", True),
        ("Give me an overview of this document", True),
        ("What does this PDF cover?", True),
        ("شو هاد الملف؟", True),
        ("لخص الملف", True),
        ("What equipment is shown in this drawing?", False),
        ("What is the latest Cisco firmware?", False),
    ],
)
def test_is_document_overview_question(question, expected):
    assert is_document_overview_question(question) is expected

def test_document_overview_routes_to_document():
    decide_query_route.__globals__[
        "is_document_overview_question"
    ] = is_document_overview_question

    result = decide_query_route(
        question="Can you tell me what the PDF is about?",
        search_mode="Documents + Web",
        has_document=True,
        content_type="DOCUMENT",
        document_scope_active=False,
        is_follow_up=False,
    )

    assert result == "DOCUMENT"

def test_document_overview_respects_web_only_mode():
    decide_query_route.__globals__[
        "is_document_overview_question"
    ] = is_document_overview_question

    result = decide_query_route(
        question="Can you tell me what the PDF is about?",
        search_mode="Web Only",
        has_document=True,
        content_type="DOCUMENT",
        document_scope_active=False,
        is_follow_up=False,
    )

    assert result == "WEB"

def test_build_document_overview_instruction_for_document_overview():
    result = build_document_overview_instruction(
        "Can you tell me what the PDF is about?",
        "DOCUMENT",
    )

    assert "Document overview instructions:" in result
    assert "Start with 1-2 sentences" in result
    assert "4-7 concise bullet points" in result
    assert "Do not lead with legal disclaimers" in result
    assert "site/building names" in result
    assert "partition wall into a screen" in result
    assert "Preserve lifecycle/disposition terms exactly" in result
    assert "established English technical term or proper noun" in result
    assert "copy the exact source noun phrase and model name" in result
    assert "do not call a codec a microphone" in result
    assert "Preserve directional and mounting descriptors exactly" in result
    assert "Do not rewrite divisible room" in result
    assert "omit the unsupported label rather than guessing" in result


def test_build_document_overview_instruction_returns_empty_for_non_overview():
    result = build_document_overview_instruction(
        "What equipment is shown in this drawing?",
        "DRAWING",
    )

    assert result == ""



def test_document_overview_fidelity_review_prompt_guards_device_identity():
    prompt = build_document_overview_fidelity_review_prompt(
        question="Can you tell me what the PDF is about?",
        context=(
            "[DOC 3] A new Poly Studio G62 codec shall be provided. "
            "A new partition sensor shall detect the operable partition status."
        ),
        answer=(
            "- A Poly Studio G62 microphone will be installed [DOC 3].\n"
            "- An end port sensor will be installed [DOC 3]."
        ),
    )

    assert "Never change a codec into a microphone" in prompt
    assert "partition sensor" in prompt
    assert "Do not invent substitute terms such as end port" in prompt
    assert "Poly Studio G62 codec" in prompt


def test_document_overview_fidelity_review_prompt_preserves_lifecycle_terms():
    prompt = build_document_overview_fidelity_review_prompt(
        question="Summarize this document",
        context=(
            "[DOC 3] The existing codec shall be decommissioned, removed, "
            "and handed over for E-waste disposal."
        ),
        answer="- The codec will be environmentally processed [DOC 3].",
    )

    assert "decommissioned" in prompt
    assert "removed" in prompt
    assert "handed over" in prompt
    assert "E-waste disposal" in prompt



def test_extractive_document_overview_preserves_exact_device_identity():
    pages = [
        {
            "source": "scope.pdf",
            "page_number": 3,
            "text": (
                "The existing meeting room AV system shall be upgraded to support "
                "divisible/combined room operation using the existing AV infrastructure "
                "wherever practical. A new Poly Studio G62 codec shall be provided as "
                "the primary video conferencing platform and integrated with the existing "
                "room AV system. The existing Codec, HDMI switcher, Scaler & wireless "
                "presentation unit shall be decommissioned, removed, and handed over "
                "for E-waste disposal in accordance with the project requirements."
            ),
        },
        {
            "source": "scope.pdf",
            "page_number": 5,
            "text": (
                "A new partition sensor shall be provided to detect the operable "
                "partition status and enable the divisible-room audio control logic. "
                "When the partition is open, the audio system shall combine the "
                "microphone and loudspeaker zones."
            ),
        },
    ]

    doc_source_numbers = {
        ("scope.pdf", 3): 3,
        ("scope.pdf", 5): 5,
    }

    result = build_extractive_document_overview(
        question="Can you tell me what the PDF is about?",
        document_pages=pages,
        doc_source_numbers=doc_source_numbers,
        source_name="scope.pdf",
        max_points=7,
    )

    assert "Poly Studio G62 codec" in result
    assert "partition sensor" in result
    assert "operable partition" in result
    assert "E-waste disposal" in result
    assert "G62 microphone" not in result
    assert "end port sensor" not in result
    assert "[DOC 3]" in result
    assert "[DOC 5]" in result


def test_clean_extractive_overview_sentence_repairs_pdf_spacing():
    result = clean_extractive_overview_sentence(
        "C amera in Room -1 supports divisible -room operation , with C odec."
    )

    assert result == (
        "Camera in Room-1 supports divisible-room operation, with Codec."
    )


def test_extractive_document_overview_prioritizes_core_scope_over_low_value_text():
    pages = [
        {
            "source": "scope.pdf",
            "page_number": 3,
            "text": (
                "See the Conferencing section for more detailed information regarding "
                "audio or video conferencing. "
                "A new Poly Studio G62 codec shall be provided as the primary video "
                "conferencing platform and integrated with the existing room AV system. "
                "The existing Codec, HDMI switcher, Scaler & wireless presentation unit "
                "shall be decommissioned, removed, and handed over for E-waste disposal."
            ),
        },
        {
            "source": "scope.pdf",
            "page_number": 5,
            "text": (
                "A new partition sensor shall be provided to detect the operable "
                "partition status and enable the divisible-room audio control logic. "
                "The microphone will be white in color."
            ),
        },
    ]

    result = build_extractive_document_overview(
        question="Can you tell me what the PDF is about?",
        document_pages=pages,
        doc_source_numbers={
            ("scope.pdf", 3): 3,
            ("scope.pdf", 5): 5,
        },
        source_name="scope.pdf",
        max_points=4,
    )

    assert "Poly Studio G62 codec" in result
    assert "E-waste disposal" in result
    assert "partition sensor" in result
    assert "See the Conferencing section" not in result
    assert "white in color" not in result


def test_extractive_document_overview_skips_legal_boilerplate():
    pages = [
        {
            "source": "scope.pdf",
            "page_number": 1,
            "text": (
                "This Entire Document and all information is proprietary information. "
                "Copyright AVI-SPL LLC. All Rights Reserved. "
                "The existing AV system shall be upgraded for divisible room operation."
            ),
        }
    ]

    result = build_extractive_document_overview(
        question="Summarize this document",
        document_pages=pages,
        doc_source_numbers={("scope.pdf", 1): 1},
        source_name="scope.pdf",
        max_points=7,
    )

    assert "The existing AV system shall be upgraded" in result
    assert "Copyright AVI-SPL" not in result
    assert "proprietary information" not in result

def test_document_overview_uses_broader_retrieval():
    result = get_document_retrieval_k(
        "Can you tell me what the PDF is about?",
        "DOCUMENT",
    )

    assert result == 12


def test_non_overview_uses_default_retrieval_depth():
    result = get_document_retrieval_k(
        "What does this document say about installation?",
        "DOCUMENT",
    )

    assert result == 4



def test_document_overview_page_selection_uses_all_pages_for_small_document():
    pages = [
        {
            "page_number": index,
            "source": "scope.pdf",
            "text": f"Page {index}",
        }
        for index in range(1, 7)
    ]

    selected = select_document_overview_pages(
        pages,
        source_name="scope.pdf",
        max_pages=12,
    )

    assert [page["page_number"] for page in selected] == [1, 2, 3, 4, 5, 6]


def test_document_overview_page_selection_is_diverse_for_large_document():
    pages = [
        {
            "page_number": index,
            "source": "manual.pdf",
            "text": f"Page {index}",
        }
        for index in range(1, 31)
    ]

    selected = select_document_overview_pages(
        pages,
        source_name="manual.pdf",
        max_pages=6,
    )

    page_numbers = [page["page_number"] for page in selected]

    assert len(page_numbers) == 6
    assert page_numbers[0] == 1
    assert page_numbers[-1] == 30
    assert len(set(page_numbers)) == 6


def test_document_overview_keeps_retrieved_evidence_before_page_context_expansion():
    evidence_documents = [
        ("page-2-chunk", 1.40, 0, 0),
        ("page-6-chunk", 1.35, 0, 0),
        ("page-4-chunk", 1.30, 0, 0),
    ]

    selected = select_relevant_documents(
        evidence_documents=evidence_documents,
        is_verification_question=False,
        question_keywords=["pdf"],
        evidence_keywords=["pdf"],
        is_document_overview=True,
    )

    assert selected == [
        "page-2-chunk",
        "page-6-chunk",
        "page-4-chunk",
    ]


def test_non_overview_still_uses_strict_evidence_filter():
    evidence_documents = [
        ("weak", 1.30, 0, 0),
        ("strong", 1.05, 0, 0),
    ]

    selected = select_relevant_documents(
        evidence_documents=evidence_documents,
        is_verification_question=False,
        question_keywords=["installation"],
        evidence_keywords=["installation"],
        is_document_overview=False,
    )

    assert selected == ["strong"]
