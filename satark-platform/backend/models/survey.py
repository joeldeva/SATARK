from sqlalchemy import Column, String, JSON, DateTime, Text, Integer, Boolean
from sqlalchemy.sql import func
import uuid
from ..app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    domain = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="draft", index=True)
    survey_data = Column(JSON, nullable=False)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    tags = Column(JSON)
    total_questions = Column(Integer, default=0)
    prepopulation_rate = Column(Integer, default=0)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, nullable=False, index=True)
    respondent_id = Column(String, index=True)
    responses = Column(JSON, nullable=False)
    coded_responses = Column(JSON)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    channel = Column(String(50))
    duration_seconds = Column(Integer)
    quality_score = Column(Integer)
    gps_latitude = Column(String(20))
    gps_longitude = Column(String(20))
    is_validated = Column(Boolean, default=False)
    validation_flags = Column(JSON)


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    user_id = Column(String(100))
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    processing_time_seconds = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50))
