import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, Enum, Integer, ForeignKey, JSON, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ComplaintStatus(str, enum.Enum):
    NEW = "New"
    UNDER_REVIEW = "Under Review"
    INVESTIGATION = "Investigation"
    CAPA = "CAPA"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class ComplaintSeverity(str, enum.Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    UNCLASSIFIED = "Unclassified"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    complaint_number = Column(String(32), unique=True, index=True)

    # Raw intake
    source_channel = Column(String(32), default="Manual")  # Email/PDF/Manual
    raw_text = Column(Text, nullable=True)

    # Structured QMS fields
    customer_name = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)
    batch_number = Column(String(100), nullable=True)
    manufacturing_date = Column(String(50), nullable=True)
    expiry_date = Column(String(50), nullable=True)
    complaint_description = Column(Text, nullable=True)
    complaint_type = Column(String(100), nullable=True)  # e.g. Quality, Packaging, Efficacy

    severity = Column(Enum(ComplaintSeverity), default=ComplaintSeverity.UNCLASSIFIED)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.NEW)

    root_cause = Column(Text, nullable=True)
    capa_notes = Column(Text, nullable=True)

    # AI outputs
    ai_completeness_score = Column(Float, nullable=True)
    ai_missing_fields = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)  # structured defect summary
    ai_suggested_action = Column(Text, nullable=True)  # recommended next step
    ai_risk_notes = Column(Text, nullable=True)  # initial risk assessment justification
    ai_raw_extraction = Column(JSON, nullable=True)

    # Chat history for the copilot session tied to this complaint
    copilot_history = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = relationship("ComplaintHistory", back_populates="complaint", cascade="all, delete-orphan")


class ComplaintHistory(Base):
    __tablename__ = "complaint_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=False), ForeignKey("complaints.id"))
    action = Column(String(255))
    note = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="history")
