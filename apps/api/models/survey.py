import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from app.database import Base


JSON_DOCUMENT = JSON().with_variant(postgresql.JSONB, "postgresql")


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
    question_graph = Column(JSON_DOCUMENT, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON)
    total_questions = Column(Integer, default=0)
    prepopulation_rate = Column(Integer, default=0)


class SurveyVersion(Base):
    """Frozen snapshots of question_graph at each publish."""

    __tablename__ = "survey_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    question_graph = Column(JSON_DOCUMENT, nullable=False)
    published_by = Column(String(100))
    published_at = Column(DateTime(timezone=True), server_default=func.now())


class AdaptiveLogicRecord(Base):
    """Per-survey adaptive branches / skip / simplify rules authored in SDRD."""

    __tablename__ = "adaptive_logic"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, nullable=False, index=True)
    trigger = Column(JSON_DOCUMENT, nullable=False)
    action = Column(String(32), nullable=False)
    target = Column(JSON_DOCUMENT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class KnowledgeSource(Base):
    """Track admin uploads ingested into RAG buckets."""

    __tablename__ = "knowledge_sources"

    id = Column(String, primary_key=True, default=generate_uuid)
    bucket = Column(String(64), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    mime_type = Column(String(120))
    byte_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    sha256 = Column(String(64), index=True)


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    user_id = Column(String(100))
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    processing_time_seconds = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50))
