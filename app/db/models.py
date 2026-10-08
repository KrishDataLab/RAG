from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.core.config import settings

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="ACTIVE")

class User(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(50), default="SystemArchitect")
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    version_label = Column(String(50), default="v1.0")
    sha256 = Column(String(64), nullable=False)
    page_count = Column(Integer, default=0)
    source_type = Column(String(50), default="HLD")
    ingestion_status = Column(String(50), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), default="user_admin")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String(50), primary_key=True)
    document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(String(100), nullable=False)
    page_number = Column(Integer, nullable=False)
    section = Column(String(255), default="General")
    subsection = Column(String(255), default="")
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Entity(Base):
    __tablename__ = "entities"
    id = Column(String(50), primary_key=True)
    document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)
    canonical_name = Column(String(255), nullable=False)
    aliases_json = Column(Text, default="[]")
    confidence = Column(Float, default=1.0)
    extraction_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

class EntitySource(Base):
    __tablename__ = "entity_sources"
    id = Column(String(50), primary_key=True)
    entity_id = Column(String(50), ForeignKey("entities.id"), nullable=False)
    document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    section = Column(String(255), default="")
    text_span = Column(Text, default="")

class EntityRelationship(Base):
    __tablename__ = "relationships"
    id = Column(String(50), primary_key=True)
    source_entity_id = Column(String(50), ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String(50), ForeignKey("entities.id"), nullable=False)
    relationship_type = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
    source_document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    source_page = Column(Integer, default=1)
    status = Column(String(50), default="ACTIVE")

class Finding(Base):
    __tablename__ = "findings"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=False)
    type = Column(String(100), nullable=False)
    severity = Column(String(50), default="MEDIUM")
    summary = Column(Text, nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="NEEDS_REVIEW")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class FindingEvidence(Base):
    __tablename__ = "finding_evidence"
    id = Column(String(50), primary_key=True)
    finding_id = Column(String(50), ForeignKey("findings.id"), nullable=False)
    document_id = Column(String(50), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    chunk_id = Column(String(100), default="")
    claim_text = Column(Text, nullable=False)

class FindingReview(Base):
    __tablename__ = "reviews"
    id = Column(String(50), primary_key=True)
    finding_id = Column(String(50), ForeignKey("findings.id"), nullable=False)
    reviewer_id = Column(String(50), default="architect_1")
    old_status = Column(String(50), default="NEEDS_REVIEW")
    new_status = Column(String(50), nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), default="system")
    project_id = Column(String(50), default="P001")
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine and Session initialization
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
