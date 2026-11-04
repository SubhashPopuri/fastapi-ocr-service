from docintel.extraction import extract_fields


def test_pan_bilingual_labels_extract_name_parent_and_indian_dob():
    ocr_text = """आयकर विभाग
INCOME TAX DEPARTMENT
स्थायी लेखा संख्या कार्ड
Permanent Account Number Card
EEXPR8234G
नाम / Name
ASHISH RAJ
पिता का नाम / Father's Name
RANJAN KUMAR SINGH
जन्म की तारीख
Date of Birth
12/07/2000
हस्ताक्षर / Signature
"""
    pages = [{"page": 1, "text": ocr_text}]

    fields = extract_fields(ocr_text, "pan_card", pages)

    assert fields["pan_number"]["value"] == "EEXPR8234G"
    assert fields["full_name"]["value"] == "ASHISH RAJ"
    assert fields["parent_name"]["value"] == "RANJAN KUMAR SINGH"
    assert fields["date_of_birth"]["value"] == "12/07/2000"
    assert fields["date_of_birth"]["normalized_value"] == "2000-07-12"


def test_pan_bilingual_labels_support_values_on_same_line():
    ocr_text = """Permanent Account Number
ABCPX1234D
Name: ARJUN KUMAR
Father's Name: RAMESH KUMAR
Date of Birth: 19/11/1990
"""
    pages = [{"page": 1, "text": ocr_text}]

    fields = extract_fields(ocr_text, "pan_card", pages)

    assert fields["full_name"]["value"] == "ARJUN KUMAR"
    assert fields["parent_name"]["value"] == "RAMESH KUMAR"
    assert fields["date_of_birth"]["normalized_value"] == "1990-11-19"
