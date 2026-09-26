from drawing_qa import (
    audit_drawing_set,
    build_connection_graph,
    build_signal_paths,
    extract_connection_index,
)


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


def test_connection_graph_resolves_output_to_input():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            SOURCE DEVICE
            TX-01
            HDMI OUT
            V0001

            DESTINATION DISPLAY
            MON-01
            HDMI IN 1
            V0001
            """,
        }
    ]

    graph = build_connection_graph(pages)
    edge = next(item for item in graph["edges"] if item["wire_id"] == "V0001")

    assert edge["status"] == "resolved"
    assert edge["source"]["device_id"] == "TX-01"
    assert edge["source"]["direction"] == "out"
    assert edge["destination"]["device_id"] == "MON-01"
    assert edge["destination"]["direction"] == "in"
    assert graph["resolved_edge_count"] == 1


def test_output_to_output_is_high_severity_review():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            SOURCE A
            TX-01
            HDMI OUT
            V0002

            SOURCE B
            VTC-01
            HDMI OUT
            V0002
            """,
        }
    ]

    audit = audit_drawing_set(pages)

    finding = next(
        item
        for item in audit["findings"]
        if item["category"] == "direction_conflict"
    )
    assert finding["severity"] == "high"
    assert "output-to-output" in finding["title"]


def test_media_family_mismatch_is_reviewed():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            VIDEO SOURCE
            TX-01
            HDMI OUT
            V0003

            NETWORK ENDPOINT
            RX-01
            RJ45 IN
            V0003
            """,
        }
    ]

    audit = audit_drawing_set(pages)

    assert any(
        item["category"] == "connector_media_mismatch"
        for item in audit["findings"]
    )


def test_ambiguous_graph_does_not_invent_direction():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            EXTRON
            SW-01
            HDMI
            V0004
            HDMI
            MON-01
            V0004
            """,
        }
    ]

    graph = build_connection_graph(pages)
    edge = next(item for item in graph["edges"] if item["wire_id"] == "V0004")

    assert edge["status"] == "ambiguous"
    assert edge["source"] is None
    assert edge["destination"] is None



def test_connection_graph_includes_traceability_and_confidence():
    pages = [
        {
            "page_number": 12,
            "source": "project.pdf",
            "text": """
            AV-305
            SOURCE
            VTC-01
            HDMI OUT
            V0100
            DESTINATION
            MON-01
            HDMI IN 1
            V0100
            """,
        }
    ]

    graph = build_connection_graph(pages)
    edge = next(item for item in graph["edges"] if item["wire_id"] == "V0100")

    assert edge["status"] == "resolved"
    assert edge["confidence"] > 0.5
    assert edge["drawings"] == ["AV-305"]
    assert edge["pages"] == [12]
    assert graph["resolution_rate"] == 1.0
    assert edge["source"]["drawing_number"] == "AV-305"
    assert edge["destination"]["drawing_number"] == "AV-305"


def test_equipment_without_connection_graph_is_verify_finding():
    pages = [
        {
            "page_number": 1,
            "source": "layout.pdf",
            "text": """
            AV-201
            SHURE
            MXA920W-S
            MIC-01
            """,
        }
    ]

    audit = audit_drawing_set(pages)
    assert any(
        item["category"] == "device_missing_from_connection_graph"
        and "MIC-01" in item["title"]
        for item in audit["findings"]
    )


def test_resolved_media_mismatch_is_high_severity_review():
    pages = [
        {
            "page_number": 20,
            "source": "signal-flow.pdf",
            "text": """
            AV-306
            SOURCE
            TX-01
            HDMI OUT
            V0200
            DESTINATION
            RX-01
            RJ45 IN
            V0200
            """,
        }
    ]

    audit = audit_drawing_set(pages)
    assert any(
        item["category"] == "resolved_media_mismatch"
        and item["severity"] == "high"
        for item in audit["findings"]
    )



def test_signal_paths_trace_source_to_terminal():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            SOURCE
            TX-01
            HDMI OUT
            V1001
            SWITCH INPUT
            SW-01
            HDMI IN
            V1001

            SWITCH OUTPUT
            SW-01
            HDMI OUT
            V1002
            DISPLAY
            MON-01
            HDMI IN 1
            V1002
            """,
        }
    ]

    graph = build_connection_graph(pages)
    paths = build_signal_paths(graph)

    assert paths["segment_count"] == 2
    assert paths["root_devices"] == ["TX-01"]
    assert paths["terminal_devices"] == ["MON-01"]
    assert any(
        path["devices"] == ["TX-01", "SW-01", "MON-01"]
        for path in paths["paths"]
    )


def test_duplicate_input_port_termination_is_high_review():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            SOURCE ONE
            TX-01
            HDMI OUT
            V1101
            DISPLAY
            MON-01
            HDMI IN 1
            V1101

            SOURCE TWO
            VTC-01
            HDMI OUT
            V1102
            DISPLAY
            MON-01
            HDMI IN 1
            V1102
            """,
        }
    ]

    audit = audit_drawing_set(pages)
    findings = [
        item for item in audit["findings"]
        if item["category"] == "duplicate_port_termination"
    ]

    assert findings
    assert findings[0]["severity"] == "high"
    assert "MON-01" in findings[0]["title"]
    assert "V1101" in findings[0]["title"]
    assert "V1102" in findings[0]["title"]


def test_directed_cycle_is_verify_not_automatic_error():
    pages = [
        {
            "page_number": 1,
            "source": "signal-flow.pdf",
            "text": """
            DEVICE A
            TX-01
            HDMI OUT
            V1201
            DEVICE B
            RX-01
            HDMI IN
            V1201

            DEVICE B
            RX-01
            HDMI OUT
            V1202
            DEVICE A
            TX-01
            HDMI IN
            V1202
            """,
        }
    ]

    audit = audit_drawing_set(pages)
    cycle_findings = [
        item for item in audit["findings"]
        if item["category"] == "directed_signal_cycle"
    ]

    assert cycle_findings
    assert cycle_findings[0]["status"] == "VERIFY"
    assert cycle_findings[0]["severity"] == "medium"
    assert audit["signal_paths"]["cycle_count"] >= 1
