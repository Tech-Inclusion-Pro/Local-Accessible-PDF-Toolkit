"""Database module for Accessible PDF Toolkit."""

from .models import (
    Base,
    User,
    Course,
    File,
    Tag,
    FileTag,
    Version,
    Setting,
    get_engine,
    get_session,
    init_db,
)
from .encryption import EncryptionManager
from .queries import DatabaseQueries
