import ast
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
