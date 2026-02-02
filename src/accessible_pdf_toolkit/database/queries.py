"""
Database query utilities for Accessible PDF Toolkit.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from .models import User, Course, File, Tag, Version, Setting, get_session, file_tags
from .encryption import hash_password, verify_password
from ..utils.constants import ComplianceStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseQueries:
    """Database query helper class."""

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize with a database session.

        Args:
            session: Optional SQLAlchemy session. Creates new if not provided.
        """
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get the database session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None

    # ==================== User Operations ====================

    def create_user(self, username: str, password: str, email: Optional[str] = None) -> User:
        """Create a new user."""
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
        )
        self.session.add(user)
        self.session.commit()
        logger.info(f"Created user: {username}")
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user and update last login."""
        user = self.session.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash):
            user.last_login = datetime.utcnow()
            self.session.commit()
            logger.info(f"User authenticated: {username}")
            return user
        logger.warning(f"Authentication failed for: {username}")
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return self.session.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.session.query(User).filter(User.username == username).first()

    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update a user's password."""
        user = self.get_user(user_id)
        if user:
            user.password_hash = hash_password(new_password)
            self.session.commit()
            return True
        return False

    # ==================== Course Operations ====================

    def create_course(
        self,
        user_id: int,
        code: str,
        name: str,
        semester: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Course:
        """Create a new course."""
        course = Course(
            user_id=user_id,
            code=code,
            name=name,
            semester=semester,
            description=description,
        )
        self.session.add(course)
        self.session.commit()
        logger.info(f"Created course: {code} - {name}")
        return course

    def get_courses(self, user_id: int) -> List[Course]:
        """Get all courses for a user."""
        return (
            self.session.query(Course)
            .filter(Course.user_id == user_id)
            .order_by(Course.semester.desc(), Course.code)
            .all()
        )

    def get_course(self, course_id: int) -> Optional[Course]:
        """Get a course by ID."""
        return self.session.query(Course).filter(Course.id == course_id).first()

    def update_course(self, course_id: int, **kwargs) -> bool:
        """Update a course's attributes."""
        course = self.get_course(course_id)
        if course:
            for key, value in kwargs.items():
                if hasattr(course, key):
                    setattr(course, key, value)
            self.session.commit()
            return True
        return False

    def delete_course(self, course_id: int) -> bool:
        """Delete a course and all associated files."""
        course = self.get_course(course_id)
        if course:
            self.session.delete(course)
            self.session.commit()
            logger.info(f"Deleted course: {course.code}")
            return True
        return False

    # ==================== File Operations ====================

    def create_file(
        self,
        original_name: str,
        file_path: str,
        file_hash: str,
        file_size: int,
        course_id: Optional[int] = None,
        **kwargs,
    ) -> File:
        """Create a new file record."""
        file = File(
            original_name=original_name,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            course_id=course_id,
            **kwargs,
        )
        self.session.add(file)
        self.session.commit()
        logger.info(f"Created file: {original_name}")
        return file

    def get_file(self, file_id: int) -> Optional[File]:
        """Get a file by ID."""
        return self.session.query(File).filter(File.id == file_id).first()

    def get_files(
        self,
        course_id: Optional[int] = None,
        compliance_status: Optional[ComplianceStatus] = None,
        tag_names: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[File]:
        """
        Get files with optional filters.

        Args:
            course_id: Filter by course
            compliance_status: Filter by compliance status
            tag_names: Filter by tags (any match)
            search_query: Search in file names
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching files
        """
        query = self.session.query(File)

        if course_id is not None:
            query = query.filter(File.course_id == course_id)

        if compliance_status is not None:
            query = query.filter(File.compliance_status == compliance_status.name)

        if tag_names:
            query = query.join(File.tags).filter(Tag.name.in_(tag_names))

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(File.original_name.ilike(search_pattern))

        return (
            query.order_by(File.modified_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def update_file(self, file_id: int, **kwargs) -> bool:
        """Update a file's attributes."""
        file = self.get_file(file_id)
        if file:
            for key, value in kwargs.items():
                if hasattr(file, key):
                    setattr(file, key, value)
            file.modified_at = datetime.utcnow()
            self.session.commit()
            return True
        return False

    def update_compliance(
        self,
        file_id: int,
        status: ComplianceStatus,
        score: Optional[float] = None,
        wcag_level: Optional[str] = None,
    ) -> bool:
        """Update a file's compliance status."""
        return self.update_file(
            file_id,
            compliance_status=status.name,
            compliance_score=score,
            wcag_level=wcag_level,
            last_validated=datetime.utcnow(),
        )

    def delete_file(self, file_id: int) -> bool:
        """Delete a file record."""
        file = self.get_file(file_id)
        if file:
            self.session.delete(file)
            self.session.commit()
            logger.info(f"Deleted file: {file.original_name}")
            return True
        return False

    # ==================== Tag Operations ====================

    def create_tag(self, name: str, color: Optional[str] = None) -> Tag:
        """Create a new tag."""
        tag = Tag(name=name, color=color)
        self.session.add(tag)
        self.session.commit()
        return tag

    def get_or_create_tag(self, name: str, color: Optional[str] = None) -> Tag:
        """Get an existing tag or create a new one."""
        tag = self.session.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = self.create_tag(name, color)
        return tag

    def get_tags(self) -> List[Tag]:
        """Get all tags."""
        return self.session.query(Tag).order_by(Tag.name).all()

    def add_tag_to_file(self, file_id: int, tag_name: str) -> bool:
        """Add a tag to a file."""
        file = self.get_file(file_id)
        if file:
            tag = self.get_or_create_tag(tag_name)
            if tag not in file.tags:
                file.tags.append(tag)
                self.session.commit()
            return True
        return False

    def remove_tag_from_file(self, file_id: int, tag_name: str) -> bool:
        """Remove a tag from a file."""
        file = self.get_file(file_id)
        if file:
            tag = self.session.query(Tag).filter(Tag.name == tag_name).first()
            if tag and tag in file.tags:
                file.tags.remove(tag)
                self.session.commit()
            return True
        return False

    # ==================== Settings Operations ====================

    def get_setting(self, user_id: int, key: str, default: str = "") -> str:
        """Get a user setting."""
        setting = (
            self.session.query(Setting)
            .filter(Setting.user_id == user_id, Setting.key == key)
            .first()
        )
        return setting.value if setting else default

    def set_setting(self, user_id: int, key: str, value: str) -> None:
        """Set a user setting."""
        setting = (
            self.session.query(Setting)
            .filter(Setting.user_id == user_id, Setting.key == key)
            .first()
        )
        if setting:
            setting.value = value
        else:
            setting = Setting(user_id=user_id, key=key, value=value)
            self.session.add(setting)
        self.session.commit()

    def get_all_settings(self, user_id: int) -> Dict[str, str]:
        """Get all settings for a user."""
        settings = self.session.query(Setting).filter(Setting.user_id == user_id).all()
        return {s.key: s.value for s in settings}

    # ==================== Analytics ====================

    def get_compliance_stats(self, user_id: int) -> Dict[str, Any]:
        """Get compliance statistics for a user's files."""
        # Get file counts by status
        files = (
            self.session.query(File)
            .join(Course)
            .filter(Course.user_id == user_id)
            .all()
        )

        status_counts = {status.name: 0 for status in ComplianceStatus}
        total_score = 0.0
        scored_count = 0

        for file in files:
            status_counts[file.compliance_status] += 1
            if file.compliance_score is not None:
                total_score += file.compliance_score
                scored_count += 1

        return {
            "total_files": len(files),
            "status_counts": status_counts,
            "average_score": total_score / scored_count if scored_count > 0 else None,
            "compliant_percentage": (
                status_counts.get(ComplianceStatus.COMPLIANT.name, 0) / len(files) * 100
                if files else 0
            ),
        }

    def get_recent_files(self, user_id: int, limit: int = 10) -> List[File]:
        """Get recently modified files for a user."""
        return (
            self.session.query(File)
            .join(Course)
            .filter(Course.user_id == user_id)
            .order_by(File.modified_at.desc())
            .limit(limit)
            .all()
        )

    def get_course_stats(self, course_id: int) -> Dict[str, Any]:
        """Get statistics for a course."""
        files = self.session.query(File).filter(File.course_id == course_id).all()

        compliant = sum(1 for f in files if f.compliance_status == ComplianceStatus.COMPLIANT.name)

        return {
            "total_files": len(files),
            "compliant_files": compliant,
            "compliance_rate": compliant / len(files) * 100 if files else 0,
            "total_size_mb": sum(f.file_size for f in files) / (1024 * 1024),
        }
