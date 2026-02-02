"""
Encryption module for secure file storage.
Uses Fernet (AES-256-GCM) for symmetric encryption.
"""

import os
import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from ..utils.constants import APP_DATA_DIR, ensure_directories
from ..utils.logger import get_logger

logger = get_logger(__name__)

KEY_FILE = APP_DATA_DIR / ".key"
SALT_FILE = APP_DATA_DIR / ".salt"


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""

    def __init__(self, password: Optional[str] = None):
        """
        Initialize the encryption manager.

        Args:
            password: Optional password for key derivation.
                     If not provided, uses machine-specific key.
        """
        ensure_directories()
        self._fernet: Optional[Fernet] = None
        self._password = password

    def _get_machine_id(self) -> bytes:
        """Get a machine-specific identifier for keyless encryption."""
        # Combine various system attributes for uniqueness
        identifiers = []

        # Username
        identifiers.append(os.getenv("USER", os.getenv("USERNAME", "default")))

        # Home directory
        identifiers.append(str(Path.home()))

        # Platform info
        import platform
        identifiers.append(platform.node())
        identifiers.append(platform.system())

        combined = ":".join(identifiers)
        return hashlib.sha256(combined.encode()).digest()

    def _get_or_create_salt(self) -> bytes:
        """Get or create a persistent salt for key derivation."""
        if SALT_FILE.exists():
            with open(SALT_FILE, "rb") as f:
                return f.read()

        salt = os.urandom(16)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        return salt

    def _derive_key(self, password: bytes) -> bytes:
        """
        Derive an encryption key from a password using PBKDF2.

        Args:
            password: Password bytes

        Returns:
            32-byte key suitable for Fernet
        """
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum
            backend=default_backend(),
        )
        key = kdf.derive(password)
        return base64.urlsafe_b64encode(key)

    def _get_fernet(self) -> Fernet:
        """Get or create the Fernet instance."""
        if self._fernet is None:
            if self._password:
                key = self._derive_key(self._password.encode())
            else:
                # Use machine-specific key for convenience
                key = self._derive_key(self._get_machine_id())

            self._fernet = Fernet(key)

        return self._fernet

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt data.

        Args:
            data: Plain bytes to encrypt

        Returns:
            Encrypted bytes
        """
        try:
            fernet = self._get_fernet()
            return fernet.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted plain bytes

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        try:
            fernet = self._get_fernet()
            return fernet.decrypt(encrypted_data)
        except InvalidToken:
            logger.error("Decryption failed: invalid token (wrong password or corrupted data)")
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file.

        Args:
            input_path: Path to file to encrypt
            output_path: Optional output path (defaults to input_path + .enc)

        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + ".enc")

        with open(input_path, "rb") as f:
            data = f.read()

        encrypted = self.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted)

        logger.debug(f"Encrypted: {input_path} -> {output_path}")
        return output_path

    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.

        Args:
            input_path: Path to encrypted file
            output_path: Optional output path (defaults to input_path without .enc)

        Returns:
            Path to decrypted file
        """
        if output_path is None:
            if input_path.suffix == ".enc":
                output_path = input_path.with_suffix("")
            else:
                output_path = input_path.with_suffix(".dec")

        with open(input_path, "rb") as f:
            encrypted = f.read()

        decrypted = self.decrypt(encrypted)

        with open(output_path, "wb") as f:
            f.write(decrypted)

        logger.debug(f"Decrypted: {input_path} -> {output_path}")
        return output_path

    def encrypt_string(self, text: str) -> str:
        """
        Encrypt a string.

        Args:
            text: Plain text

        Returns:
            Base64-encoded encrypted string
        """
        encrypted = self.encrypt(text.encode("utf-8"))
        return base64.b64encode(encrypted).decode("ascii")

    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plain text
        """
        encrypted = base64.b64decode(encrypted_text.encode("ascii"))
        decrypted = self.decrypt(encrypted)
        return decrypted.decode("utf-8")

    def change_password(self, old_password: str, new_password: str, data: bytes) -> bytes:
        """
        Re-encrypt data with a new password.

        Args:
            old_password: Current password
            new_password: New password
            data: Encrypted data

        Returns:
            Data encrypted with new password
        """
        # Decrypt with old password
        old_manager = EncryptionManager(old_password)
        decrypted = old_manager.decrypt(data)

        # Encrypt with new password
        new_manager = EncryptionManager(new_password)
        return new_manager.encrypt(decrypted)

    @staticmethod
    def generate_password(length: int = 32) -> str:
        """
        Generate a secure random password.

        Args:
            length: Password length

        Returns:
            Random password string
        """
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def verify_encryption(self, data: bytes) -> bool:
        """
        Verify that data can be decrypted with current key.

        Args:
            data: Encrypted data

        Returns:
            True if decryption succeeds
        """
        try:
            self.decrypt(data)
            return True
        except (InvalidToken, Exception):
            return False


def hash_password(password: str) -> str:
    """
    Hash a password for storage.

    Args:
        password: Plain password

    Returns:
        Hashed password string
    """
    import bcrypt
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain password
        password_hash: Stored hash

    Returns:
        True if password matches
    """
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False
