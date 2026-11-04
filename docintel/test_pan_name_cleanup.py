from docintel.extraction import _clean_pan_name_candidate, extract_fields


def test_pan_layout_name_drops_mixed_case_ocr_spillover():
    pages = [{
        "page": 1,
        "text": "RAHUL GUPTA Cae ae\nSURESH GUPTA\n23/11/1974",
    }]
    fields = extract_fields(
        "RAHUL GUPTA Cae ae\nSURESH GUPTA\n23/11/1974\n"
        "Permanent Account Number\nABCDE1234F",
        "pan_card",
        pages,
    )

    assert fields["full_name"]["value"] == "RAHUL GUPTA"
    assert fields["full_name"]["source"]["text"] == "RAHUL GUPTA Cae ae"
    assert fields["parent_name"]["value"] == "SURESH GUPTA"


def test_pan_name_cleanup_preserves_multiword_uppercase_names():
    assert _clean_pan_name_candidate("ARJUN KUMAR SAMPLE") == "ARJUN KUMAR SAMPLE"


def test_pan_name_cleanup_preserves_title_case_names():
    assert _clean_pan_name_candidate("Rahul Gupta") == "Rahul Gupta"
