from docintel.extraction import extract_fields


def test_pan_dob_does_not_return_generic_label_ocr_debris():
    text = """Permanent Account Number Card
ABCPX1234D
Name / ARJUN KUMAR
Father's Name / RAMESH KUMAR
Date of Birth = <
"""
    fields = extract_fields(text, "pan_card", [{"page": 1, "text": text}])

    assert "date_of_birth" not in fields
