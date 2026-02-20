"""
Audit logger for tracking before/after changes during PDF remediation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.models import AuditLogEntry, get_session
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Tracks changes made during remediation for audit trail and reporting."""

    def __init__(self, file_id: int, user_id: Optional[int] = None):
        """
        Initialize the audit logger.

        Args:
            file_id: Database file ID for the document being remediated
            user_id: Optional user ID performing the remediation
        """
        self._file_id = file_id
        self._user_id = user_id

    def log_change(
        self,
        action: str,
        criterion: Optional[str] = None,
        original_value: Optional[str] = None,
        new_value: Optional[str] = None,
        element_description: Optional[str] = None,
        page: Optional[int] = None,
    ) -> None:
        """
        Log a single remediation change.

        Args:
            action: Action identifier (e.g. "set_title", "add_alt_text")
            criterion: WCAG criterion ID (e.g. "2.4.2")
            original_value: Value before the change
            new_value: Value after the change
            element_description: Description of the affected element
            page: Page number if applicable
        """
        try:
            session = get_session()
            entry = AuditLogEntry(
                file_id=self._file_id,
                user_id=self._user_id,
                action=action,
                criterion=criterion,
                page=page,
                original_value=original_value,
                new_value=new_value,
                element_description=element_description,
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            session.commit()
            session.close()
            logger.debug(f"Audit log: {action} [{criterion}] on page {page}")
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def get_log(self) -> List[AuditLogEntry]:
        """
        Get all audit log entries for this file, newest first.

        Returns:
            List of AuditLogEntry objects
        """
        try:
            session = get_session()
            entries = (
                session.query(AuditLogEntry)
                .filter(AuditLogEntry.file_id == self._file_id)
                .order_by(AuditLogEntry.created_at.desc())
                .all()
            )
            session.close()
            return entries
        except Exception as e:
            logger.warning(f"Failed to read audit log: {e}")
            return []

    def get_log_summary(self) -> Dict[str, Any]:
        """
        Get a summary of changes for report generation.

        Returns:
            Dict with total_changes count and actions list
        """
        entries = self.get_log()
        actions = []
        for entry in entries:
            actions.append({
                "action": entry.action,
                "criterion": entry.criterion,
                "page": entry.page,
                "original_value": entry.original_value,
                "new_value": entry.new_value,
                "element_description": entry.element_description,
                "timestamp": entry.created_at.isoformat() if entry.created_at else None,
            })
        return {
            "total_changes": len(actions),
            "actions": actions,
        }
