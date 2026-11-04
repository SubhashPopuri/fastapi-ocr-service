from docintel.integrations.workday.adapter import MockWorkdayAdapter
def test_workday_mock_maps_fields_without_external_write():
    result={"request_id":"req-test","extracted_data":{"invoice_number":{"value":"INV-1","normalized_value":"INV-1"},"total_amount":{"value":"$10","normalized_value":"10.00"}}}
    adapter=MockWorkdayAdapter({"invoice_number":"Invoice_Reference","total_amount":"Invoice_Total"})
    output=adapter.submit(result)
    assert output["status"]=="simulated"
    assert output["integration"]["payload"]=={"Invoice_Reference":"INV-1","Invoice_Total":"10.00"}
    assert output["integration"]["submission_enabled"] is False
