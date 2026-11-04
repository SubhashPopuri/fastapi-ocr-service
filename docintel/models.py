"""Canonical response contracts."""
from typing import Any,Dict,List,Optional
from pydantic import BaseModel,Field
class SourceEvidence(BaseModel):
    page:Optional[int]=None
    text:Optional[str]=None
    method:Optional[str]=None
    bounding_box:Optional[Dict[str,float]]=None
class ExtractedField(BaseModel):
    value:Any=None
    confidence:Optional[float]=None
    source:Optional[SourceEvidence]=None
    validation_status:str="not_checked"
    warnings:List[str]=Field(default_factory=list)
class Classification(BaseModel):
    document_type:str
    method:str="rules"
    confidence:Optional[float]=None
    evidence:List[str]=Field(default_factory=list)
    review_required:bool=False
class ValidationResult(BaseModel):
    is_valid:bool
    errors:List[Dict[str,str]]=Field(default_factory=list)
    warnings:List[Dict[str,str]]=Field(default_factory=list)
class DocumentMetadata(BaseModel):
    filename:str
    media_type:str
    document_type:str
    page_count:int=1
    size_bytes:int
class ProcessingMetadata(BaseModel):
    methods:List[str]=Field(default_factory=list)
    ocr_used:bool=False
    duration_ms:int
class DocumentResponse(BaseModel):
    request_id:str
    status:str
    document:DocumentMetadata
    classification:Classification
    extracted_data:Dict[str,ExtractedField]
    tables:List[Dict[str,Any]]=Field(default_factory=list)
    validation:ValidationResult
    review_required:bool=False
    processing:ProcessingMetadata
    warnings:List[str]=Field(default_factory=list)
    raw_text:Optional[str]=None
