"""
Document profile memory — remembers previous sessions per document.
"""

import hashlib
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..database.models import DocumentProfile, get_session
from ..core.wcag_validator import ValidationResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProfileManager:
    """Manages document profiles for cross-session memory."""

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def get_profile(file_path: Path) -> Optional[DocumentProfile]:
        """
        Look up a document profile by file hash.

        Args:
            file_path: Path to the PDF file

        Returns:
            DocumentProfile if found, else None
        """
        try:
            file_hash = DocumentProfileManager.compute_file_hash(file_path)
            session = get_session()
            profile = (
                session.query(DocumentProfile)
                .filter(DocumentProfile.file_hash == file_hash)
                .first()
            )
            session.close()
            return profile
        except Exception as e:
            logger.warning(f"Failed to get document profile: {e}")
            return None

    @staticmethod
    def save_session(file_path: Path, result: ValidationResult) -> Optional[DocumentProfile]:
        """
        Save or update a document profile after a validation session.

        Args:
            file_path: Path to the PDF file
            result: Current validation result

        Returns:
            Updated DocumentProfile
        """
        try:
            file_hash = DocumentProfileManager.compute_file_hash(file_path)
            issues_json = json.dumps([
                {"criterion": i.criterion, "severity": i.severity.value, "message": i.message}
                for i in result.issues
            ])
            resolved = json.dumps(result.passed_criteria)

            session = get_session()
            profile = (
                session.query(DocumentProfile)
                .filter(DocumentProfile.file_hash == file_hash)
                .first()
            )

            if profile:
                profile.last_session_date = datetime.utcnow()
                profile.last_score = result.score
                profile.last_issues_json = issues_json
                profile.resolved_criteria = resolved
                profile.session_count += 1
                profile.file_path = str(file_path)
            else:
                profile = DocumentProfile(
                    file_hash=file_hash,
                    file_path=str(file_path),
                    original_name=file_path.name,
                    last_session_date=datetime.utcnow(),
                    last_score=result.score,
                    last_issues_json=issues_json,
                    resolved_criteria=resolved,
                    session_count=1,
                )
                session.add(profile)

            session.commit()
            session.close()
            return profile
        except Exception as e:
            logger.warning(f"Failed to save document profile: {e}")
            return None

    @staticmethod
    def compare_sessions(file_path: Path, current_result: ValidationResult) -> Dict[str, Any]:
        """
        Compare the current session with the previous one.

        Args:
            file_path: Path to the PDF file
            current_result: Current validation result

        Returns:
            Dict with comparison data
        """
        profile = DocumentProfileManager.get_profile(file_path)

        if not profile or not profile.last_issues_json:
            return {
                "is_returning": False,
                "previous_score": None,
                "current_score": current_result.score,
                "new_issues": [],
                "resolved_issues": [],
                "persistent_issues": [],
                "session_count": 0,
            }

        try:
            previous_issues = json.loads(profile.last_issues_json)
        except (json.JSONDecodeError, TypeError):
            previous_issues = []

        prev_keys = {(i["criterion"], i["message"]) for i in previous_issues}
        curr_keys = {(i.criterion, i.message) for i in current_result.issues}

        new_issues = [k for k in curr_keys if k not in prev_keys]
        resolved_issues = [k for k in prev_keys if k not in curr_keys]
        persistent_issues = [k for k in curr_keys if k in prev_keys]

        return {
            "is_returning": True,
            "previous_score": profile.last_score,
            "current_score": current_result.score,
            "new_issues": new_issues,
            "resolved_issues": resolved_issues,
            "persistent_issues": persistent_issues,
            "session_count": profile.session_count,
        }
