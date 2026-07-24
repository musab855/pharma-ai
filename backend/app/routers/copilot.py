import io
import pypdf
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional


from .. import crud, schemas, models
from ..database import get_db
from ..langgraph_agent.graph import run_copilot

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

EDITABLE_KEYS = crud.EDITABLE_KEYS + ["severity"]


def _fields_snapshot(complaint: models.Complaint) -> dict:
    return {k: getattr(complaint, k) for k in EDITABLE_KEYS}


@router.post("/message", response_model=schemas.CopilotMessageOut)
def copilot_message(payload: schemas.CopilotMessageIn, db: Session = Depends(get_db)):
    is_new = not payload.complaint_id
    complaint = None
    existing_fields = {}

    if not is_new:
        complaint = db.query(models.Complaint).filter_by(id=payload.complaint_id).first()
        if not complaint:
            raise HTTPException(404, "Complaint not found")
        existing_fields = _fields_snapshot(complaint)

    result = run_copilot(payload.message, existing_fields, is_new)

    if is_new:
        complaint = crud.create_complaint_from_copilot(db, payload.message, result)
    else:
        if result.get("intent") == "edit_existing":
            complaint = crud.apply_copilot_edit(db, complaint, result)
        # general_chat: no field changes, just reply

    crud.append_copilot_turn(db, complaint, payload.message, result.get("reply", ""), result.get("tool_used", "chat"))

    return schemas.CopilotMessageOut(
        reply=result.get("reply", ""),
        tool_used=result.get("tool_used", "chat"),
        complaint=complaint,
    )


@router.post("/upload", response_model=schemas.CopilotMessageOut)
async def copilot_upload(
    complaint_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Document Extraction tool: reads an uploaded complaint file (plain text or PDF)

    and feeds it through the same Log/Edit Complaint pipeline.
    """
    raw_bytes = await file.read()
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    # Extract text based on file type
    if ext == "pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            extracted_pages = [
                page.extract_text()
                for page in reader.pages
                if page.extract_text()
            ]
            text = "\n".join(extracted_pages)
        except Exception as e:
            raise HTTPException(
                400, f"Failed to extract text from PDF file: {str(e)}"
            )
    else:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="ignore")

    # CRITICAL: PostgreSQL crashes on null bytes (0x00). Strip them out.
    text = text.replace("\x00", "").strip()

    if not text:
        raise HTTPException(
            400,
            f"Could not extract any readable text from '{file.filename}'. "
            "If this is a scanned document or image PDF, OCR is required.",
        )

    is_new = not complaint_id
    complaint = None
    existing_fields = {}

    if not is_new:
        complaint = (
            db.query(models.Complaint).filter_by(id=complaint_id).first()
        )
        if not complaint:
            raise HTTPException(404, "Complaint not found")
        existing_fields = _fields_snapshot(complaint)

    result = run_copilot(text, existing_fields, is_new)

    if is_new:
        complaint = crud.create_complaint_from_copilot(db, text, result)
        complaint.source_channel = "Document Upload"
        db.commit()
        db.refresh(complaint)
    else:
        if result.get("intent") == "edit_existing":
            complaint = crud.apply_copilot_edit(db, complaint, result)

    reply = f"Extracted data from **{file.filename}**. " + result.get("reply", "")
    crud.append_copilot_turn(
        db,
        complaint,
        f"[Uploaded file: {file.filename}]",
        reply,
        "document_extraction_tool",
    )

    return schemas.CopilotMessageOut(
        reply=reply,
        tool_used="document_extraction_tool",
        complaint=complaint,
    )