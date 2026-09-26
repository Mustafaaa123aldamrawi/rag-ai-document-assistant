from PIL import Image

from drawing_visual import (
    build_drawing_region_messages,
    parse_drawing_region_analysis,
    reconcile_visual_with_connection_graph,
    select_visual_qa_pages,
    split_drawing_image_into_regions,
)


def test_signal_flow_pages_are_prioritized_for_visual_qa():
    pages = [
        {"page_number": 1, "text": "COVER SHEET"},
        {"page_number": 2, "text": "FLOOR PLAN AV LAYOUT"},
        {"page_number": 3, "text": "AV SIGNAL FLOW DIAGRAM - 7 PAX MEETING ROOM"},
        {"page_number": 4, "text": "DIVISIBLE MEETING ROOM CEILING PLAN"},
    ]
    selected = select_visual_qa_pages(pages, max_pages=2)
    assert selected[0] == 3
    assert 4 in selected


def test_findings_increase_page_priority():
    pages = [
        {"page_number": 1, "text": "FLOOR PLAN AV LAYOUT"},
        {"page_number": 2, "text": "FLOOR PLAN AV LAYOUT"},
    ]
    qa = {
        "findings": [
            {
                "severity": "high",
                "evidence": [{"page_number": 2}],
            }
        ]
    }
    selected = select_visual_qa_pages(pages, qa, max_pages=1)
    assert selected == [2]


def test_drawing_image_is_split_into_four_overlapping_regions():
    image = Image.new("RGB", (1000, 800), "white")
    regions = split_drawing_image_into_regions(image)
    assert len(regions) == 4
    assert regions[0]["region_number"] == 1
    assert regions[-1]["region_number"] == 4
    assert all(region["image"].width > 0 for region in regions)
    assert all(region["image"].height > 0 for region in regions)


def test_drawing_region_prompt_is_strict_and_visual():
    messages = build_drawing_region_messages(
        file_name="shop-drawings.pdf",
        page_number=12,
        region_number=2,
        image_data_url="data:image/jpeg;base64,abc",
    )
    assert messages[0]["role"] == "system"
    user_content = messages[1]["content"]
    assert user_content[1]["type"] == "image_url"
    assert "Do not infer the opposite endpoint" in user_content[0]["text"]


def test_drawing_region_json_parser_repairs_trailing_comma():
    raw = """
    {
      "drawing_number": "AV-305",
      "room_labels": ["Divisible Meeting Room"],
      "device_blocks": [],
      "connections": [],
      "visible_requirements": [],
      "possible_issues": [],
      "uncertainties": [],
    }
    """
    parsed = parse_drawing_region_analysis(raw)
    assert parsed["drawing_number"] == "AV-305"
    assert parsed["room_labels"] == ["Divisible Meeting Room"]


def test_drawing_region_parser_normalizes_missing_lists():
    parsed = parse_drawing_region_analysis('{"drawing_number":"AV-301"}')
    assert parsed["device_blocks"] == []
    assert parsed["connections"] == []
    assert parsed["possible_issues"] == []



def test_visual_reconciliation_confirms_matching_connection():
    qa = {
        "connection_graph": {
            "edges": [
                {
                    "wire_id": "V0001",
                    "status": "resolved",
                    "confidence": 0.9,
                    "pages": [12],
                    "source": {
                        "device_id": "TX-01",
                        "port": "HDMI OUT",
                    },
                    "destination": {
                        "device_id": "MON-01",
                        "port": "HDMI IN 1",
                    },
                }
            ]
        }
    }
    visual = {
        "regions": [
            {
                "page_number": 12,
                "region_number": 2,
                "drawing_number": "AV-305",
                "connections": [
                    {
                        "wire_id": "V0001",
                        "source_device": "TX-01",
                        "source_port": "HDMI OUT",
                        "destination_device": "MON-01",
                        "destination_port": "HDMI IN 1",
                        "signal_type": "video",
                        "connector_type": "HDMI",
                        "confidence": "high",
                        "evidence": "Wire V0001 visibly links both device blocks.",
                    }
                ],
            }
        ]
    }

    result = reconcile_visual_with_connection_graph(qa, visual)

    assert result["confirmed_count"] == 1
    assert result["conflict_count"] == 0
    assert result["confirmed"][0]["status"] == "VISUALLY_CONFIRMED"
    assert result["confirmation_rate"] == 1.0


def test_visual_reconciliation_flags_endpoint_conflict():
    qa = {
        "connection_graph": {
            "edges": [
                {
                    "wire_id": "V0002",
                    "status": "resolved",
                    "confidence": 0.88,
                    "pages": [20],
                    "source": {"device_id": "TX-01", "port": "HDMI OUT"},
                    "destination": {"device_id": "MON-01", "port": "HDMI IN 1"},
                }
            ]
        }
    }
    visual = {
        "regions": [
            {
                "page_number": 20,
                "region_number": 1,
                "connections": [
                    {
                        "wire_id": "V0002",
                        "source_device": "TX-01",
                        "source_port": "HDMI OUT",
                        "destination_device": "MON-02",
                        "destination_port": "HDMI IN 1",
                        "confidence": "high",
                        "evidence": "Visible destination label reads MON-02.",
                    }
                ],
            }
        ]
    }

    result = reconcile_visual_with_connection_graph(qa, visual)

    assert result["confirmed_count"] == 0
    assert result["conflict_count"] == 1
    assert result["conflicts"][0]["status"] == "CONFLICT_REVIEW"
    assert result["conflicts"][0]["severity"] == "high"


def test_visual_reconciliation_preserves_unmatched_visual_wire():
    qa = {"connection_graph": {"edges": []}}
    visual = {
        "regions": [
            {
                "page_number": 3,
                "region_number": 1,
                "connections": [
                    {
                        "wire_id": "C0999",
                        "source_device": "CU-01",
                        "destination_device": "MON-01",
                        "confidence": "medium",
                    }
                ],
            }
        ]
    }

    result = reconcile_visual_with_connection_graph(qa, visual)

    assert result["visual_only_count"] == 1
    assert result["visual_only"][0]["wire_id"] == "C0999"
