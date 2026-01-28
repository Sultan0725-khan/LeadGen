from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.timezone import get_german_now
import uuid
import enum
from app.database import Base


class RunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(Base):
    """Lead generation run."""
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(Enum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    location = Column(String, nullable=False)
    category = Column(String, nullable=False)
    require_approval = Column(Integer, default=0)  # SQLite boolean
    dry_run = Column(Integer, default=0)  # SQLite boolean
    total_leads = Column(Integer, default=0)
    is_pinned = Column(Integer, default=0)  # SQLite boolean

    # Provider selection and limits
    selected_providers = Column(JSON, default=list)  # List of provider IDs used
    provider_limits = Column(JSON, default=dict)  # Dict of provider_id -> query limit

    # Enrichment statistics
    total_emails = Column(Integer, default=0)  # Count of leads with email
    total_websites = Column(Integer, default=0)  # Count of leads with website
    total_drafts = Column(Integer, default=0)   # Count of leads with an email draft
    total_sent = Column(Integer, default=0)     # Count of leads with a sent email
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_german_now)
    updated_at = Column(DateTime, default=get_german_now, onupdate=get_german_now)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    leads = relationship("Lead", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="run", cascade="all, delete-orphan")
