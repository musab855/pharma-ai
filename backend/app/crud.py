import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from . import models


def gen_complaint_number(db: Session) -> str:
    year = datetime.utcnow().year
    while True:
        suffix = "".join(random.choices(string.digits, k=5))
        number = f"CMP-{year}-{suffix}"
        exists = db.query(models.Complaint).filter_by(complaint_number=number).first()
        if not exists:
            return number


def create_complaint(db: Session, raw_text: str, source_channel: str = "Manual") -> models.Complaint:
    complaint = models.Complaint(
        complaint_number=gen_complaint_number(db),
        source_channel=source_channel,
        raw_text=raw_text,
        status=models.ComplaintStatus.NEW,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    log_history(db, complaint.id, "Complaint created", f"Received via {source_channel}")
    return complaint


def apply_ai_results(db: Session, complaint: models.Complaint, ai_state: dict) -> models.Complaint:
    complaint.customer_name = ai_state.get("customer_name")
    complaint.product_name = ai_state.get("product_name")
    complaint.batch_number = ai_state.get("batch_number")
    complaint.manufacturing_date = ai_state.get("manufacturing_date")
    complaint.complaint_description = ai_state.get("complaint_description")
    complaint.complaint_type = ai_state.get("complaint_type")

    severity = ai_state.get("suggested_severity") or "Unclassified"
    if severity not in [s.value for s in models.ComplaintSeverity]:
        severity = "Unclassified"
    complaint.severity = severity

    complaint.ai_completeness_score = ai_state.get("completeness_score")
    complaint.ai_missing_fields = ai_state.get("missing_fields")
    complaint.ai_summary = ai_state.get("summary")
    complaint.ai_raw_extraction = ai_state.get("extraction_raw")

    db.commit()
    db.refresh(complaint)
    log_history(db, complaint.id, "AI processing complete",
                f"Completeness score: {complaint.ai_completeness_score}%")
    return complaint


EDITABLE_KEYS = [
    "customer_name", "product_name", "batch_number", "manufacturing_date",
    "expiry_date", "complaint_description", "complaint_type",
]


def create_complaint_from_copilot(db: Session, raw_message: str, result: dict) -> models.Complaint:
    complaint = models.Complaint(
        complaint_number=gen_complaint_number(db),
        source_channel="Copilot",
        raw_text=raw_message,
        status=models.ComplaintStatus.NEW,
        copilot_history=[],
    )
    for key in EDITABLE_KEYS:
        setattr(complaint, key, result.get(key))

    severity = result.get("severity") or "Unclassified"
    if severity not in [s.value for s in models.ComplaintSeverity]:
        severity = "Unclassified"
    complaint.severity = severity

    complaint.ai_completeness_score = result.get("completeness_score")
    complaint.ai_missing_fields = result.get("missing_fields")
    complaint.ai_summary = result.get("summary")
    complaint.ai_suggested_action = result.get("suggested_action")
    complaint.ai_risk_notes = result.get("risk_notes")
    complaint.ai_raw_extraction = result.get("extraction_raw")

    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    log_history(db, complaint.id, "Complaint logged via AI Copilot",
                f"Severity: {complaint.severity}, completeness: {complaint.ai_completeness_score}%")
    return complaint


def apply_copilot_edit(db: Session, complaint: models.Complaint, result: dict) -> models.Complaint:
    changed = result.get("edited_field_names", [])
    for key in changed:
        if key in EDITABLE_KEYS:
            setattr(complaint, key, result.get(key))
        elif key == "severity":
            pass  # severity handled below via risk_assessment output regardless

    severity = result.get("severity") or complaint.severity
    if severity not in [s.value for s in models.ComplaintSeverity]:
        severity = complaint.severity
    complaint.severity = severity

    complaint.ai_summary = result.get("summary", complaint.ai_summary)
    complaint.ai_suggested_action = result.get("suggested_action", complaint.ai_suggested_action)
    complaint.ai_risk_notes = result.get("risk_notes", complaint.ai_risk_notes)

    db.commit()
    db.refresh(complaint)
    log_history(db, complaint.id, "Fields edited via AI Copilot",
                f"Changed: {', '.join(changed) if changed else 'none'}")
    return complaint


def append_copilot_turn(db: Session, complaint: models.Complaint, user_message: str, reply: str, tool_used: str):
    history = complaint.copilot_history or []
    history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply, "tool_used": tool_used},
    ]
    complaint.copilot_history = history
    db.commit()
    db.refresh(complaint)


def log_history(db: Session, complaint_id: str, action: str, note: str = None):
    entry = models.ComplaintHistory(complaint_id=complaint_id, action=action, note=note)
    db.add(entry)
    db.commit()


VALID_TRANSITIONS = {
    "New": {"Under Review", "Rejected"},
    "Under Review": {"Investigation", "Rejected"},
    "Investigation": {"CAPA", "Closed"},
    "CAPA": {"Closed"},
    "Closed": set(),
    "Rejected": set(),
}


def update_status(db: Session, complaint: models.Complaint, new_status: str, note: str = None):
    current = complaint.status.value if hasattr(complaint.status, "value") else complaint.status
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid transition from '{current}' to '{new_status}'. Allowed: {allowed or 'none'}")
    complaint.status = new_status
    db.commit()
    db.refresh(complaint)
    log_history(db, complaint.id, f"Status changed to {new_status}", note)
    return complaint
