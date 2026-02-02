"""
File operation utilities for Accessible PDF Toolkit.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List, BinaryIO
from datetime import datetime
import tempfile

from .constants import (
    TEMP_DIR,
    CACHE_DIR,
    SUPPORTED_INPUT_FORMATS,
    MAX_FILE_SIZE_MB,
    ensure_directories,
)
from .logger import get_logger

logger = get_logger(__name__)


class FileOperations:
    """Utility class for file operations."""

    @staticmethod
    def validate_pdf(file_path: Path) -> tuple[bool, str]:
        """
        Validate a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
            return False, f"Unsupported file format: {file_path.suffix}"

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return False, f"File too large: {size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"

        # Check PDF magic bytes
        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF"):
                    return False, "Invalid PDF file (missing PDF header)"
        except IOError as e:
            return False, f"Cannot read file: {e}"

        return True, ""

    @staticmethod
    def calculate_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """
        Calculate file hash for integrity checking.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (default: sha256)

        Returns:
            Hex digest of the hash
        """
        hash_func = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def get_temp_path(prefix: str = "apt_", suffix: str = "") -> Path:
        """
        Get a temporary file path.

        Args:
            prefix: Filename prefix
            suffix: Filename suffix

        Returns:
            Path to temporary file
        """
        ensure_directories()
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=TEMP_DIR)
        os.close(fd)
        return Path(path)

    @staticmethod
    def get_cache_path(key: str, extension: str = "") -> Path:
        """
        Get a cache file path based on a key.

        Args:
            key: Cache key
            extension: File extension

        Returns:
            Path to cache file
        """
        ensure_directories()
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return CACHE_DIR / f"{hash_key}{extension}"

    @staticmethod
    def safe_copy(src: Path, dst: Path, overwrite: bool = False) -> bool:
        """
        Safely copy a file with atomic write.

        Args:
            src: Source path
            dst: Destination path
            overwrite: Whether to overwrite existing files

        Returns:
            True if successful
        """
        if dst.exists() and not overwrite:
            logger.warning(f"Destination exists, skipping: {dst}")
            return False

        try:
            # Copy to temp location first
            temp_dst = dst.with_suffix(dst.suffix + ".tmp")
            shutil.copy2(src, temp_dst)

            # Atomic rename
            temp_dst.rename(dst)
            logger.debug(f"Copied: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            if temp_dst.exists():
                temp_dst.unlink()
            return False

    @staticmethod
    def safe_write(file_path: Path, content: bytes) -> bool:
        """
        Safely write content to file with atomic write.

        Args:
            file_path: Destination path
            content: Content to write

        Returns:
            True if successful
        """
        try:
            # Write to temp file first
            temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
            with open(temp_path, "wb") as f:
                f.write(content)

            # Atomic rename
            temp_path.rename(file_path)
            logger.debug(f"Wrote: {file_path} ({len(content)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Write failed: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False

    @staticmethod
    def safe_delete(file_path: Path) -> bool:
        """
        Safely delete a file.

        Args:
            file_path: Path to delete

        Returns:
            True if successful
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    @staticmethod
    def cleanup_temp_files(max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files.

        Args:
            max_age_hours: Maximum age in hours before deletion

        Returns:
            Number of files deleted
        """
        ensure_directories()
        deleted = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        for file_path in TEMP_DIR.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    deleted += 1
                except Exception as e:
                    logger.warning(f"Could not delete temp file {file_path}: {e}")

        if deleted:
            logger.info(f"Cleaned up {deleted} temporary files")
        return deleted

    @staticmethod
    def get_unique_filename(directory: Path, base_name: str, extension: str) -> Path:
        """
        Generate a unique filename in a directory.

        Args:
            directory: Target directory
            base_name: Base filename (without extension)
            extension: File extension (with dot)

        Returns:
            Unique file path
        """
        candidate = directory / f"{base_name}{extension}"
        counter = 1

        while candidate.exists():
            candidate = directory / f"{base_name}_{counter}{extension}"
            counter += 1

        return candidate

    @staticmethod
    def ensure_parent_directory(file_path: Path) -> None:
        """
        Ensure the parent directory of a file exists.

        Args:
            file_path: File path
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_file_info(file_path: Path) -> dict:
        """
        Get information about a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information
        """
        if not file_path.exists():
            return {}

        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.absolute()),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
        }

    @staticmethod
    def list_files(
        directory: Path,
        extensions: Optional[List[str]] = None,
        recursive: bool = False,
    ) -> List[Path]:
        """
        List files in a directory.

        Args:
            directory: Directory to list
            extensions: Filter by extensions (e.g., [".pdf", ".html"])
            recursive: Search recursively

        Returns:
            List of file paths
        """
        if not directory.exists():
            return []

        if recursive:
            files = list(directory.rglob("*"))
        else:
            files = list(directory.iterdir())

        files = [f for f in files if f.is_file()]

        if extensions:
            extensions = [e.lower() for e in extensions]
            files = [f for f in files if f.suffix.lower() in extensions]

        return sorted(files, key=lambda f: f.name.lower())
