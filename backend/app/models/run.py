from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
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
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    leads = relationship("Lead", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="run", cascade="all, delete-orphan")
