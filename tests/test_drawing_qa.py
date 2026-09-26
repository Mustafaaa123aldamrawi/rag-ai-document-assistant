from drawing_qa import audit_drawing_set, extract_connection_index


def test_connection_index_and_single_ended_wire():
    pages = [
        {
            "page_number": 1,
            "source": "sample.pdf",
            "text": """
            EXTRON
            IN1608
            VTC-01
            HDMI OUT HDMI
            V0001
            """,
        }
    ]
    index = extract_connection_index(pages)
    assert "V0001" in index["wires"]

    audit = audit_drawing_set(pages)
    assert any(
        item["category"] == "single_ended_connection"
        for item in audit["findings"]
    )


def test_conflicting_device_identity_is_flagged():
    pages = [
        {
            "page_number": 1,
            "source": "sample.pdf",
            "text": """
            SHURE
            MXA920W-S
            MIC-01
            D0001
            """,
        },
        {
            "page_number": 2,
            "source": "sample.pdf",
            "text": """
            BIAMP
            Parle TCM-X
            MIC-01
            D0001
            """,
        },
    ]

    audit = audit_drawing_set(pages)
    assert any(
        item["category"] == "device_identity_conflict"
        for item in audit["findings"]
    )


def test_programming_requirements_are_vendor_specific():
    pages = [
        {
            "page_number": 1,
            "source": "sample.pdf",
            "text": """
            LIGHTWARE
            UCX-1x1-C40
            TX-01
            V0001
            """,
        },
        {
            "page_number": 2,
            "source": "sample.pdf",
            "text": """
            CRESTRON
            GLS-PART-CN
            OCS-01
            C0001
            """,
        },
    ]
    audit = audit_drawing_set(pages)
    vendors = {item["vendor"] for item in audit["programming_requirements"]}
    assert "LIGHTWARE" in vendors
    assert "CRESTRON" in vendors
