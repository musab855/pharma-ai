from typing import TypedDict, Optional, List, Dict, Any


class CopilotState(TypedDict, total=False):
    message: str
    existing_fields: Dict[str, Any]  # current DB values if editing an existing complaint
    is_new: bool

    intent: str  # log_new | edit_existing | general_chat

    # merged/working field values (existing + extracted/edited)
    customer_name: Optional[str]
    product_name: Optional[str]
    batch_number: Optional[str]
    manufacturing_date: Optional[str]
    expiry_date: Optional[str]
    complaint_description: Optional[str]
    complaint_type: Optional[str]
    severity: Optional[str]

    extraction_raw: Dict[str, Any]
    edited_field_names: List[str]

    completeness_score: float
    missing_fields: List[Dict[str, str]]

    summary: str
    suggested_action: str
    risk_notes: str

    reply: str
    tool_used: str
