"""
SQLAlchemy database models for Accessible PDF Toolkit.
"""

from datetime import datetime
from typing import Optional, List
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    LargeBinary,
    Float,
    Enum as SQLEnum,
    Table,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
    Session,
    Mapped,
    mapped_column,
)
from sqlalchemy.engine import Engine

from ..utils.constants import DATABASE_FILE, ComplianceStatus, WCAGLevel, ensure_directories


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    versions: Mapped[List["Version"]] = relationship("Version", back_populates="user")
    settings: Mapped[List["Setting"]] = relationship("Setting", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Course(Base):
    """Course model for organizing files."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="courses")
    files: Mapped[List["File"]] = relationship("File", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_courses_user_code", "user_id", "code"),
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, code='{self.code}', name='{self.name}')>"


# Association table for many-to-many relationship between files and tags
file_tags = Table(
    "file_tags",
    Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class File(Base):
    """File model for storing PDF metadata and encrypted content."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tagged_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    html_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Compliance information
    compliance_status: Mapped[str] = mapped_column(
        String(20), default=ComplianceStatus.NOT_CHECKED.name
    )
    compliance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wcag_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_validated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Encrypted content (optional - for sensitive documents)
    encrypted_content: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Relationships
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True)
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="files")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=file_tags, back_populates="files")
    versions: Mapped[List["Version"]] = relationship("Version", back_populates="file", cascade="all, delete-orphan")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_files_course", "course_id"),
        Index("ix_files_compliance", "compliance_status"),
        Index("ix_files_hash", "file_hash"),
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, name='{self.original_name}')>"


class Tag(Base):
    """Tag model for categorizing files."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    files: Mapped[List["File"]] = relationship("File", secondary=file_tags, back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"


# Alias for backwards compatibility with plan
FileTag = file_tags


class Version(Base):
    """Version model for tracking file changes."""

    __tablename__ = "versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[str] = mapped_column(String(20), nullable=False)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    file: Mapped["File"] = relationship("File", back_populates="versions")
    user: Mapped["User"] = relationship("User", back_populates="versions")

    __table_args__ = (
        Index("ix_versions_file", "file_id"),
        Index("ix_versions_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Version(id={self.id}, version_id='{self.version_id}')>"


class Setting(Base):
    """User settings model."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")

    __table_args__ = (
        Index("ix_settings_user_key", "user_id", "key", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Setting(user_id={self.user_id}, key='{self.key}')>"


# Global engine and session factory
_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def get_engine(database_path: Optional[Path] = None) -> Engine:
    """
    Get or create the database engine.

    Args:
        database_path: Optional custom database path

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine

    if _engine is None:
        ensure_directories()
        db_path = database_path or DATABASE_FILE
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            future=True,
        )

    return _engine


def get_session() -> Session:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session instance
    """
    global _SessionFactory

    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    return _SessionFactory()


def init_db(database_path: Optional[Path] = None) -> None:
    """
    Initialize the database, creating all tables.

    Args:
        database_path: Optional custom database path
    """
    engine = get_engine(database_path)
    Base.metadata.create_all(engine)
