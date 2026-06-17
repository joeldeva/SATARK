from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from sqlalchemy.types import CHAR, TypeDecorator

from app.database import Base


class GUID(TypeDecorator):
    """Use native UUID on Postgres and stable text UUIDs elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


JSON_DOCUMENT = JSON().with_variant(postgresql.JSONB, "postgresql")


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", GUID(), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


def uuid_pk():
    return Column(GUID(), primary_key=True, default=uuid.uuid4)


class Permission(Base):
    __tablename__ = "permissions"

    id = uuid_pk()
    code = Column(String(80), unique=True, nullable=False, index=True)
    description = Column(String(255), default="")


class Role(Base):
    __tablename__ = "roles"

    id = uuid_pk()
    code = Column(String(24), unique=True, nullable=False, index=True)
    name = Column(String(80), nullable=False)
    permissions = Column(JSON_DOCUMENT, default=list, nullable=False)


class PlatformUser(Base):
    __tablename__ = "users"

    id = uuid_pk()
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(24), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EnumeratorProfile(Base):
    __tablename__ = "enumerators"

    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    region = Column(String(160), nullable=False)
    assigned = Column(Integer, default=0, nullable=False)
    completed = Column(Integer, default=0, nullable=False)
    trust_score = Column(Float, default=100, nullable=False)
    trust_level = Column(String(16), default="Green", nullable=False)
    trust_trend = Column(JSON_DOCUMENT, default=list, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Household(Base):
    __tablename__ = "households"

    id = Column(String(64), primary_key=True)
    prepopulated = Column(JSON_DOCUMENT, default=dict, nullable=False)


class Assignment(Base):
    __tablename__ = "assignments"

    id = uuid_pk()
    survey_id = Column(String(80), nullable=False, index=True)
    enumerator_id = Column(String(64), ForeignKey("enumerators.id"), nullable=False, index=True)
    household_id = Column(String(64), ForeignKey("households.id"), nullable=True, index=True)
    status = Column(String(24), default="assigned", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConsentRecord(Base):
    __tablename__ = "consents"

    id = uuid_pk()
    survey_id = Column(String(80), nullable=False, index=True)
    household_id = Column(String(64), ForeignKey("households.id"), nullable=True, index=True)
    enumerator_id = Column(String(64), ForeignKey("enumerators.id"), nullable=True, index=True)
    consented = Column(Boolean, default=True, nullable=False)
    language = Column(String(16))
    payload = Column(JSON_DOCUMENT, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IntelligenceSession(Base):
    __tablename__ = "intelligence_sessions"

    id = uuid_pk()
    survey_id = Column(String(80), nullable=False, index=True)
    household_id = Column(String(64), ForeignKey("households.id"), nullable=True, index=True)
    enumerator_id = Column(String(64), ForeignKey("enumerators.id"), nullable=True, index=True)
    status = Column(String(24), default="active", nullable=False, index=True)
    payload = Column(JSON_DOCUMENT, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Response(Base):
    __tablename__ = "responses"

    id = uuid_pk()
    survey_id = Column(String(80), nullable=False, index=True)
    enumerator_id = Column(String(64), ForeignKey("enumerators.id"), nullable=True, index=True)
    household_id = Column(String(64), ForeignKey("households.id"), nullable=True, index=True)
    channel = Column(String(32), default="web", nullable=False)
    answers = Column(JSON_DOCUMENT, default=dict, nullable=False)
    prepopulated = Column(JSON_DOCUMENT, default=dict, nullable=False)
    adaptive_log = Column(JSON_DOCUMENT, default=list, nullable=False)
    confidence_score = Column(Float)
    trust_level = Column(String(16), index=True)
    status = Column(String(24), default="captured", nullable=False, index=True)
    # Tamper-evident hash chain (Postgres-backed, blockchain-style — no blockchain).
    content_hash = Column(Text, nullable=False, default="")
    prev_hash = Column(Text)
    chain_index = Column(Integer, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResponseVersion(Base):
    __tablename__ = "response_versions"

    id = uuid_pk()
    response_id = Column(GUID(), ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    answers = Column(JSON_DOCUMENT, default=dict, nullable=False)
    changed_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    reason = Column(String(255), default="", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Paradata(Base):
    __tablename__ = "paradata"

    id = uuid_pk()
    response_id = Column(GUID(), ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    total_seconds = Column(Integer)
    question_timings = Column(JSON_DOCUMENT, default=dict, nullable=False)
    pauses = Column(Integer, default=0, nullable=False)
    correction_count = Column(Integer, default=0, nullable=False)
    back_nav_count = Column(Integer, default=0, nullable=False)
    gps_lat = Column(Float)
    gps_lng = Column(Float)
    device = Column(String(120))
    mode = Column(String(32))
    network = Column(String(32))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = uuid_pk()
    response_id = Column(GUID(), ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    layer = Column(String(40), nullable=False)
    field = Column(String(80))
    status = Column(String(16), nullable=False)
    severity = Column(String(16), nullable=False)
    reason = Column(Text, nullable=False)
    recommended_action = Column(String(40))
    confidence = Column(Float)  # 0..100 — this method's confidence in the answer
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = uuid_pk()
    response_id = Column(GUID(), ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String(16), nullable=False, index=True)
    breakdown = Column(JSON_DOCUMENT, default=dict, nullable=False)
    fraud_signals = Column(JSON_DOCUMENT, default=list, nullable=False)
    recommendation = Column(String(40), nullable=False)
    reasons = Column(JSON_DOCUMENT, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CodingResult(Base):
    __tablename__ = "coding_results"

    id = uuid_pk()
    response_id = Column(GUID(), ForeignKey("responses.id", ondelete="CASCADE"), nullable=True, index=True)
    field = Column(String(80), nullable=False)
    raw_text = Column(Text, nullable=False)
    suggestions = Column(JSON_DOCUMENT, default=list, nullable=False)
    approved_code = Column(String(32))
    approved_label = Column(String(255))
    source = Column(String(80), default="local", nullable=False)
    confidence = Column(Float, default=0, nullable=False)
    needs_review = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ValidationRuleRecord(Base):
    __tablename__ = "validation_rules"

    id = uuid_pk()
    survey_id = Column(String(80), nullable=False, index=True)
    field = Column(String(80), nullable=False)
    rule_type = Column(String(32), nullable=False)
    params = Column(JSON_DOCUMENT, default=dict, nullable=False)
    severity = Column(String(16), default="error", nullable=False)
    reason_template = Column(String(255), default="", nullable=False)


class ReferenceDistribution(Base):
    __tablename__ = "reference_distributions"

    id = uuid_pk()
    key = Column(String(80), nullable=False, index=True)
    stratum = Column(String(120), default="all", nullable=False)
    p05 = Column(Float)
    median = Column(Float)
    p95 = Column(Float)
    params = Column(JSON_DOCUMENT, default=dict, nullable=False)


class ClassificationCode(Base):
    __tablename__ = "classification_codes"

    id = uuid_pk()
    code = Column(String(32), nullable=False, index=True)
    code_type = Column(String(24), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    synonyms = Column(JSON_DOCUMENT, default=list, nullable=False)
    external_source = Column(String(120))
    family = Column(String(255), nullable=True)
    sector = Column(String(255), nullable=True, index=True)
    level = Column(String(24), nullable=True)
    section = Column(String(24), nullable=True, index=True)
    parent_code = Column(String(32), nullable=True, index=True)


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (UniqueConstraint("bucket", "chunk_id", name="uq_rag_chunks_bucket_chunk_id"),)

    id = uuid_pk()
    bucket = Column(String(64), nullable=False, index=True)
    chunk_id = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(JSON_DOCUMENT, default=list, nullable=False)
    metadata_json = Column(JSON_DOCUMENT, default=dict, nullable=False)
    source_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MockIdentity(Base):
    """DEMO ONLY — a mock government identity registry for the prepopulation
    pattern. There is NO real Aadhaar/UIDAI integration and no checksum
    validation; any well-formed input is accepted. Seeded with a handful of
    fictitious records purely to demonstrate field prefill from a household
    record."""

    __tablename__ = "mock_identities"

    id = uuid_pk()
    id_type = Column(String(24), nullable=False, index=True)  # aadhaar | voter | ration
    id_number = Column(String(40), nullable=False)            # masked display form
    last4 = Column(String(8), nullable=False, index=True)     # match key (suffix)
    name = Column(String(120))
    district = Column(String(120))
    village = Column(String(120))
    lgd_code = Column(String(40))
    household_size = Column(Integer)
    last_occupation = Column(String(80))
    record = Column(JSON_DOCUMENT, default=dict, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = uuid_pk()
    actor = Column(String(120), nullable=False)
    action = Column(String(120), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(120), nullable=False)
    payload = Column(JSON_DOCUMENT, default=dict, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
