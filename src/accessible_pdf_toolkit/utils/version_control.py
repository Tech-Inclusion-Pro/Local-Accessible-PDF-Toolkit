"""
Version control utilities for tracking document changes.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict
import hashlib

from .constants import APP_DATA_DIR, ensure_directories
from .logger import get_logger
from .file_operations import FileOperations

logger = get_logger(__name__)

VERSIONS_DIR = APP_DATA_DIR / "versions"


@dataclass
class VersionInfo:
    """Information about a document version."""

    version_id: str
    file_id: int
    user_id: int
    description: str
    created_at: str
    file_hash: str
    snapshot_path: str
    size_bytes: int


class VersionControl:
    """Manages document versions and snapshots."""

    def __init__(self):
        ensure_directories()
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def create_version(
        self,
        file_path: Path,
        file_id: int,
        user_id: int,
        description: str = "",
    ) -> Optional[VersionInfo]:
        """
        Create a new version snapshot of a file.

        Args:
            file_path: Path to the file to snapshot
            file_id: Database file ID
            user_id: User who created the version
            description: Description of changes

        Returns:
            VersionInfo or None if failed
        """
        if not file_path.exists():
            logger.error(f"Cannot create version: file not found: {file_path}")
            return None

        try:
            # Generate version ID
            timestamp = datetime.now()
            version_id = self._generate_version_id(file_id, timestamp)

            # Create snapshot directory
            snapshot_dir = VERSIONS_DIR / str(file_id)
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Copy file to snapshot location
            snapshot_path = snapshot_dir / f"{version_id}{file_path.suffix}"
            shutil.copy2(file_path, snapshot_path)

            # Calculate hash
            file_hash = FileOperations.calculate_hash(file_path)

            # Create version info
            version = VersionInfo(
                version_id=version_id,
                file_id=file_id,
                user_id=user_id,
                description=description,
                created_at=timestamp.isoformat(),
                file_hash=file_hash,
                snapshot_path=str(snapshot_path),
                size_bytes=file_path.stat().st_size,
            )

            # Save metadata
            self._save_version_metadata(version)

            logger.info(f"Created version {version_id} for file {file_id}")
            return version

        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            return None

    def get_versions(self, file_id: int) -> List[VersionInfo]:
        """
        Get all versions for a file.

        Args:
            file_id: Database file ID

        Returns:
            List of VersionInfo sorted by creation date (newest first)
        """
        snapshot_dir = VERSIONS_DIR / str(file_id)
        if not snapshot_dir.exists():
            return []

        versions = []
        metadata_file = snapshot_dir / "versions.json"

        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    for v in data.get("versions", []):
                        versions.append(VersionInfo(**v))
            except Exception as e:
                logger.error(f"Failed to load version metadata: {e}")

        # Sort by creation date, newest first
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions

    def get_version(self, file_id: int, version_id: str) -> Optional[VersionInfo]:
        """
        Get a specific version.

        Args:
            file_id: Database file ID
            version_id: Version identifier

        Returns:
            VersionInfo or None
        """
        versions = self.get_versions(file_id)
        for version in versions:
            if version.version_id == version_id:
                return version
        return None

    def restore_version(
        self,
        file_id: int,
        version_id: str,
        target_path: Path,
    ) -> bool:
        """
        Restore a file to a specific version.

        Args:
            file_id: Database file ID
            version_id: Version to restore
            target_path: Where to restore the file

        Returns:
            True if successful
        """
        version = self.get_version(file_id, version_id)
        if not version:
            logger.error(f"Version not found: {version_id}")
            return False

        snapshot_path = Path(version.snapshot_path)
        if not snapshot_path.exists():
            logger.error(f"Snapshot file not found: {snapshot_path}")
            return False

        try:
            # Create a new version of current state before restoring
            if target_path.exists():
                self.create_version(
                    target_path,
                    file_id,
                    version.user_id,
                    f"Auto-backup before restore to {version_id}",
                )

            # Restore the file
            shutil.copy2(snapshot_path, target_path)
            logger.info(f"Restored file {file_id} to version {version_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore version: {e}")
            return False

    def delete_version(self, file_id: int, version_id: str) -> bool:
        """
        Delete a specific version.

        Args:
            file_id: Database file ID
            version_id: Version to delete

        Returns:
            True if successful
        """
        version = self.get_version(file_id, version_id)
        if not version:
            return False

        try:
            # Delete snapshot file
            snapshot_path = Path(version.snapshot_path)
            if snapshot_path.exists():
                snapshot_path.unlink()

            # Update metadata
            versions = [v for v in self.get_versions(file_id) if v.version_id != version_id]
            self._save_versions_list(file_id, versions)

            logger.info(f"Deleted version {version_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete version: {e}")
            return False

    def cleanup_old_versions(
        self,
        file_id: int,
        keep_count: int = 10,
    ) -> int:
        """
        Remove old versions, keeping only the most recent ones.

        Args:
            file_id: Database file ID
            keep_count: Number of versions to keep

        Returns:
            Number of versions deleted
        """
        versions = self.get_versions(file_id)
        if len(versions) <= keep_count:
            return 0

        to_delete = versions[keep_count:]
        deleted = 0

        for version in to_delete:
            if self.delete_version(file_id, version.version_id):
                deleted += 1

        return deleted

    def compare_versions(
        self,
        file_id: int,
        version_id_1: str,
        version_id_2: str,
    ) -> dict:
        """
        Compare two versions of a file.

        Args:
            file_id: Database file ID
            version_id_1: First version
            version_id_2: Second version

        Returns:
            Dictionary with comparison results
        """
        v1 = self.get_version(file_id, version_id_1)
        v2 = self.get_version(file_id, version_id_2)

        if not v1 or not v2:
            return {"error": "Version not found"}

        return {
            "version_1": asdict(v1),
            "version_2": asdict(v2),
            "size_diff": v2.size_bytes - v1.size_bytes,
            "hash_match": v1.file_hash == v2.file_hash,
            "time_diff_seconds": (
                datetime.fromisoformat(v2.created_at)
                - datetime.fromisoformat(v1.created_at)
            ).total_seconds(),
        }

    def _generate_version_id(self, file_id: int, timestamp: datetime) -> str:
        """Generate a unique version ID."""
        data = f"{file_id}:{timestamp.isoformat()}"
        return hashlib.sha1(data.encode()).hexdigest()[:12]

    def _save_version_metadata(self, version: VersionInfo) -> None:
        """Save version metadata to JSON file."""
        versions = self.get_versions(version.file_id)

        # Check if version already exists
        versions = [v for v in versions if v.version_id != version.version_id]
        versions.insert(0, version)

        self._save_versions_list(version.file_id, versions)

    def _save_versions_list(self, file_id: int, versions: List[VersionInfo]) -> None:
        """Save list of versions to JSON file."""
        snapshot_dir = VERSIONS_DIR / str(file_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = snapshot_dir / "versions.json"

        data = {
            "file_id": file_id,
            "versions": [asdict(v) for v in versions],
        }

        with open(metadata_file, "w") as f:
            json.dump(data, f, indent=2)
