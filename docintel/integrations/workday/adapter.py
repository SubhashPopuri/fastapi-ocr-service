"""Workday payload preparation; no tenant API calls are made by this adapter."""
import hashlib,json
from ..base import IntegrationAdapter
from .mapper import WorkdayFieldMapper
class WorkdayAdapter(IntegrationAdapter):
    def __init__(self,field_map=None):
        self.mapper=WorkdayFieldMapper(field_map)
    def prepare(self,document_result):
        payload=self.mapper.map_fields(document_result.get("extracted_data",{}))
        stable=json.dumps({"request_id":document_result.get("request_id"),"payload":payload},sort_keys=True,default=str)
        return {"target":"workday","payload":payload,"idempotency_key":hashlib.sha256(stable.encode()).hexdigest(),"submission_enabled":False}
class MockWorkdayAdapter(WorkdayAdapter):
    """Safe local adapter for demos/tests; simulates acceptance without network writes."""
    def submit(self,document_result):
        prepared=self.prepare(document_result)
        return {"status":"simulated","message":"Mock adapter accepted payload; no Workday tenant was contacted.","integration":prepared}
