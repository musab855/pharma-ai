from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

# NOTE: Complaints are created via the AI Copilot (see routers/copilot.py — Log Complaint
# tool), not through a manual form endpoint, per the "AI must fill the form" requirement.
# This router handles listing, viewing, status transitions, and manual corrections
# after the copilot has done the initial intake.


@router.get("/", response_model=List[schemas.ComplaintOut])
def list_complaints(db: Session = Depends(get_db)):
    return db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).all()


@router.get("/{complaint_id}", response_model=schemas.ComplaintOut)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter_by(id=complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    return complaint


@router.patch("/{complaint_id}/status", response_model=schemas.ComplaintOut)
def change_status(complaint_id: str, payload: schemas.ComplaintUpdateStatus, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter_by(id=complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    try:
        return crud.update_status(db, complaint, payload.status, payload.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/{complaint_id}/fields", response_model=schemas.ComplaintOut)
def update_fields(complaint_id: str, payload: schemas.ComplaintUpdateFields, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter_by(id=complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(complaint, field, value)
    db.commit()
    db.refresh(complaint)
    crud.log_history(db, complaint.id, "Fields manually edited")
    return complaint

