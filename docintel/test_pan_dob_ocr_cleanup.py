from docintel.extraction import extract_fields


def test_pan_dob_replaces_generic_ocr_punctuation_with_real_date():
    text = """Permanent Account Number Card
EEXPR8234G
Name / ASHISH RAJ
Father's Name / RANJAN KUMAR SINGH
Date of Birth = <
12/07/2000
"""
    fields = extract_fields(text, "pan_card", [{"page": 1, "text": text}])

    assert fields["date_of_birth"]["value"] == "12/07/2000"
    assert fields["date_of_birth"]["normalized_value"] == "2000-07-12"
    assert fields["date_of_birth"]["source"]["method"] == "pan_dob_pattern"


def test_pan_dob_ignores_invalid_date_and_accepts_day_first_format():
    text = """Permanent Account Number Card
ABCPX1234D
Date of Birth
31/02/2000
12/07/2000
"""
    fields = extract_fields(text, "pan_card", [{"page": 1, "text": text}])

    assert fields["date_of_birth"]["value"] == "12/07/2000"
    assert fields["date_of_birth"]["normalized_value"] == "2000-07-12"
