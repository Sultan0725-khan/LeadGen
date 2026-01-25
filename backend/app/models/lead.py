from sqlalchemy import Column, String, DateTime, Float, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.timezone import get_german_now
import uuid
from app.database import Base


class Lead(Base):
    """Business lead with enrichment data."""
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)

    # Core business info
    business_name = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Metadata
    confidence_score = Column(Float, default=0.0)
    sources = Column(JSON, default=list)  # List of provider names
    enrichment_data = Column(JSON, default=dict)  # Social profiles, additional contacts
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_german_now)
    updated_at = Column(DateTime, default=get_german_now, onupdate=get_german_now)

    # Relationships
    run = relationship("Run", back_populates="leads")
    email_record = relationship("Email", back_populates="lead", uselist=False)
    logs = relationship("Log", back_populates="lead", cascade="all, delete-orphan")
