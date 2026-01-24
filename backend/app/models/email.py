from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base


class EmailStatus(str, enum.Enum):
    DRAFTED = "drafted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class Email(Base):
    """Generated and sent emails."""
    __tablename__ = "emails"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)

    status = Column(Enum(EmailStatus), default=EmailStatus.DRAFTED, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    language = Column(String, default="DE")

    generated_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="email_record")


class OptOut(Base):
    """Email opt-out/unsubscribe list."""
    __tablename__ = "optout_list"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    optout_at = Column(DateTime, default=datetime.utcnow)
