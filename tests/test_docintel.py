from docintel.classification import classify
from docintel.extraction import extract_fields,validate_fields
from docintel.pipeline import process_document
def test_invoice_classification():
    assert classify("TAX INVOICE Invoice Number: INV-1 Amount Due: 100")["document_type"]=="invoice"
def test_schema_extraction():
    text="Invoice Number: INV-100\nInvoice Date: 2026-11-04\nTotal Amount: 1250"
    fields=extract_fields(text,"invoice",[{"page":1,"text":text}])
    assert fields["invoice_number"]["value"]=="INV-100"
    assert validate_fields(fields,"invoice")["is_valid"]
def test_unknown_fallback():
    assert classify("A page containing unlabelled prose")["document_type"]=="general_document"
def test_text_pipeline_raw_text_opt_in():
    result=process_document("invoice.txt",b"Invoice Number: INV-200\nInvoice Date: 2026-11-04\nTotal Amount: 200","text/plain")
    assert result["document"]["document_type"]=="invoice"
    assert result["extracted_data"]["invoice_number"]["value"]=="INV-200"
    assert "raw_text" not in result
