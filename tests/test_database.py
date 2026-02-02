"""Tests for database module."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from accessible_pdf_toolkit.database.models import (
    Base,
    User,
    Course,
    File,
    Tag,
    Version,
    Setting,
    get_engine,
    get_session,
    init_db,
)
from accessible_pdf_toolkit.database.queries import DatabaseQueries
from accessible_pdf_toolkit.utils.constants import ComplianceStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        yield db_path


@pytest.fixture
def db_queries(temp_db):
    """Create a DatabaseQueries instance with test database."""
    queries = DatabaseQueries()
    yield queries
    queries.close()


class TestUserOperations:
    """Tests for user-related database operations."""

    def test_create_user(self, db_queries):
        """Test creating a new user."""
        user = db_queries.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )

        assert user is not None
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_authenticate_user(self, db_queries):
        """Test user authentication."""
        db_queries.create_user("authuser", "password123")

        # Correct password
        user = db_queries.authenticate_user("authuser", "password123")
        assert user is not None
        assert user.username == "authuser"

        # Wrong password
        user = db_queries.authenticate_user("authuser", "wrongpass")
        assert user is None

    def test_get_user(self, db_queries):
        """Test getting user by ID."""
        created = db_queries.create_user("getuser", "pass123")

        user = db_queries.get_user(created.id)
        assert user is not None
        assert user.username == "getuser"

    def test_get_user_by_username(self, db_queries):
        """Test getting user by username."""
        db_queries.create_user("findme", "pass123")

        user = db_queries.get_user_by_username("findme")
        assert user is not None
        assert user.username == "findme"

        # Non-existent user
        user = db_queries.get_user_by_username("notfound")
        assert user is None

    def test_update_password(self, db_queries):
        """Test updating user password."""
        user = db_queries.create_user("passuser", "oldpass")

        success = db_queries.update_password(user.id, "newpass")
        assert success is True

        # Verify new password works
        auth_user = db_queries.authenticate_user("passuser", "newpass")
        assert auth_user is not None


class TestCourseOperations:
    """Tests for course-related database operations."""

    def test_create_course(self, db_queries):
        """Test creating a new course."""
        user = db_queries.create_user("courseuser", "pass")

        course = db_queries.create_course(
            user_id=user.id,
            code="CS101",
            name="Intro to CS",
            semester="Fall 2024",
        )

        assert course is not None
        assert course.code == "CS101"
        assert course.name == "Intro to CS"

    def test_get_courses(self, db_queries):
        """Test getting all courses for a user."""
        user = db_queries.create_user("multiuser", "pass")
        db_queries.create_course(user.id, "CS101", "Course 1")
        db_queries.create_course(user.id, "CS102", "Course 2")

        courses = db_queries.get_courses(user.id)
        assert len(courses) == 2

    def test_update_course(self, db_queries):
        """Test updating a course."""
        user = db_queries.create_user("updateuser", "pass")
        course = db_queries.create_course(user.id, "OLD101", "Old Name")

        success = db_queries.update_course(
            course.id,
            code="NEW101",
            name="New Name",
        )
        assert success is True

        updated = db_queries.get_course(course.id)
        assert updated.code == "NEW101"
        assert updated.name == "New Name"

    def test_delete_course(self, db_queries):
        """Test deleting a course."""
        user = db_queries.create_user("deluser", "pass")
        course = db_queries.create_course(user.id, "DEL101", "Delete Me")

        success = db_queries.delete_course(course.id)
        assert success is True

        deleted = db_queries.get_course(course.id)
        assert deleted is None


class TestFileOperations:
    """Tests for file-related database operations."""

    def test_create_file(self, db_queries):
        """Test creating a new file record."""
        file = db_queries.create_file(
            original_name="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size=1024,
        )

        assert file is not None
        assert file.original_name == "test.pdf"
        assert file.file_hash == "abc123"

    def test_get_files_with_filters(self, db_queries):
        """Test getting files with various filters."""
        user = db_queries.create_user("fileuser", "pass")
        course = db_queries.create_course(user.id, "FILE101", "Files")

        db_queries.create_file("doc1.pdf", "/path/doc1.pdf", "hash1", 100, course.id)
        db_queries.create_file("doc2.pdf", "/path/doc2.pdf", "hash2", 200, course.id)

        # All files
        files = db_queries.get_files(course_id=course.id)
        assert len(files) == 2

        # Search filter
        files = db_queries.get_files(search_query="doc1")
        assert len(files) >= 1

    def test_update_compliance(self, db_queries):
        """Test updating file compliance status."""
        file = db_queries.create_file("comp.pdf", "/path/comp.pdf", "hash", 100)

        success = db_queries.update_compliance(
            file.id,
            status=ComplianceStatus.COMPLIANT,
            score=95.5,
            wcag_level="AA",
        )
        assert success is True

        updated = db_queries.get_file(file.id)
        assert updated.compliance_status == "COMPLIANT"
        assert updated.compliance_score == 95.5


class TestTagOperations:
    """Tests for tag-related database operations."""

    def test_create_tag(self, db_queries):
        """Test creating a tag."""
        tag = db_queries.create_tag("Important", "#FF0000")

        assert tag is not None
        assert tag.name == "Important"
        assert tag.color == "#FF0000"

    def test_get_or_create_tag(self, db_queries):
        """Test get or create tag functionality."""
        # Create new
        tag1 = db_queries.get_or_create_tag("NewTag")
        assert tag1 is not None

        # Get existing
        tag2 = db_queries.get_or_create_tag("NewTag")
        assert tag2.id == tag1.id

    def test_add_tag_to_file(self, db_queries):
        """Test adding a tag to a file."""
        file = db_queries.create_file("tagged.pdf", "/path", "hash", 100)

        success = db_queries.add_tag_to_file(file.id, "Reviewed")
        assert success is True

        updated = db_queries.get_file(file.id)
        assert len(updated.tags) == 1
        assert updated.tags[0].name == "Reviewed"

    def test_remove_tag_from_file(self, db_queries):
        """Test removing a tag from a file."""
        file = db_queries.create_file("untagged.pdf", "/path", "hash", 100)
        db_queries.add_tag_to_file(file.id, "ToRemove")

        success = db_queries.remove_tag_from_file(file.id, "ToRemove")
        assert success is True

        updated = db_queries.get_file(file.id)
        assert len(updated.tags) == 0


class TestSettingsOperations:
    """Tests for settings-related database operations."""

    def test_set_and_get_setting(self, db_queries):
        """Test setting and getting a setting."""
        user = db_queries.create_user("settingsuser", "pass")

        db_queries.set_setting(user.id, "theme", "dark")

        value = db_queries.get_setting(user.id, "theme")
        assert value == "dark"

    def test_get_setting_default(self, db_queries):
        """Test getting a setting with default value."""
        user = db_queries.create_user("defaultuser", "pass")

        value = db_queries.get_setting(user.id, "nonexistent", "default_value")
        assert value == "default_value"

    def test_get_all_settings(self, db_queries):
        """Test getting all settings for a user."""
        user = db_queries.create_user("allsettings", "pass")
        db_queries.set_setting(user.id, "key1", "value1")
        db_queries.set_setting(user.id, "key2", "value2")

        settings = db_queries.get_all_settings(user.id)
        assert len(settings) == 2
        assert settings["key1"] == "value1"


class TestAnalytics:
    """Tests for analytics functions."""

    def test_get_compliance_stats(self, db_queries):
        """Test getting compliance statistics."""
        user = db_queries.create_user("statsuser", "pass")
        course = db_queries.create_course(user.id, "STAT101", "Stats")

        f1 = db_queries.create_file("f1.pdf", "/p1", "h1", 100, course.id)
        f2 = db_queries.create_file("f2.pdf", "/p2", "h2", 100, course.id)

        db_queries.update_compliance(f1.id, ComplianceStatus.COMPLIANT, 95.0)
        db_queries.update_compliance(f2.id, ComplianceStatus.PARTIAL, 60.0)

        stats = db_queries.get_compliance_stats(user.id)

        assert stats["total_files"] == 2
        assert stats["status_counts"]["COMPLIANT"] == 1
        assert stats["average_score"] is not None

    def test_get_recent_files(self, db_queries):
        """Test getting recent files."""
        user = db_queries.create_user("recentuser", "pass")
        course = db_queries.create_course(user.id, "REC101", "Recent")

        db_queries.create_file("old.pdf", "/old", "h1", 100, course.id)
        db_queries.create_file("new.pdf", "/new", "h2", 100, course.id)

        recent = db_queries.get_recent_files(user.id, limit=5)
        assert len(recent) == 2
