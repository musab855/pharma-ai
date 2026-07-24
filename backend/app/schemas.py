from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class ComplaintCreate(BaseModel):
    source_channel: str = "Manual"
    raw_text: str


class ComplaintUpdateStatus(BaseModel):
    status: str
    note: Optional[str] = None


class ComplaintUpdateFields(BaseModel):
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    complaint_description: Optional[str] = None
    complaint_type: Optional[str] = None
    severity: Optional[str] = None
    root_cause: Optional[str] = None
    capa_notes: Optional[str] = None


class HistoryOut(BaseModel):
    action: str
    note: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class ComplaintOut(BaseModel):
    id: str
    complaint_number: Optional[str]
    source_channel: str
    raw_text: Optional[str]
    customer_name: Optional[str]
    product_name: Optional[str]
    batch_number: Optional[str]
    manufacturing_date: Optional[str]
    expiry_date: Optional[str]
    complaint_description: Optional[str]
    complaint_type: Optional[str]
    severity: str
    status: str
    root_cause: Optional[str]
    capa_notes: Optional[str]
    ai_completeness_score: Optional[float]
    ai_missing_fields: Optional[Any]
    ai_summary: Optional[str]
    ai_suggested_action: Optional[str]
    ai_risk_notes: Optional[str]
    ai_raw_extraction: Optional[Any]
    copilot_history: Optional[Any]
    created_at: datetime
    updated_at: datetime
    history: List[HistoryOut] = []

    class Config:
        from_attributes = True


class CopilotMessageIn(BaseModel):
    complaint_id: Optional[str] = None
    message: str


class CopilotMessageOut(BaseModel):
    reply: str
    tool_used: str
    complaint: ComplaintOut
