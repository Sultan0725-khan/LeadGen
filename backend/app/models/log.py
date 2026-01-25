from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.timezone import get_german_now
import uuid
import enum
from app.database import Base


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Log(Base):
    """System logs with structured context."""
    __tablename__ = "logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("runs.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    level = Column(Enum(LogLevel), default=LogLevel.INFO, nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSON, default=dict)  # Additional metadata

    created_at = Column(DateTime, default=get_german_now)

    # Relationships
    run = relationship("Run", back_populates="logs")
    lead = relationship("Lead", back_populates="logs")
