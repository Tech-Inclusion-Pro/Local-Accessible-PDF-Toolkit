"""Tests for encryption module."""

import pytest
import tempfile
from pathlib import Path

from accessible_pdf_toolkit.database.encryption import (
    EncryptionManager,
    hash_password,
    verify_password,
)


class TestEncryptionManager:
    """Tests for EncryptionManager class."""

    def test_encrypt_decrypt_bytes(self):
        """Test encrypting and decrypting bytes."""
        manager = EncryptionManager()
        original = b"This is sensitive data"

        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)

        assert encrypted != original
        assert decrypted == original

    def test_encrypt_decrypt_with_password(self):
        """Test encryption with password."""
        password = "test_password_123"
        manager = EncryptionManager(password=password)
        original = b"Secret information"

        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == original

    def test_wrong_password_fails(self):
        """Test that wrong password fails decryption."""
        manager1 = EncryptionManager(password="correct_password")
        manager2 = EncryptionManager(password="wrong_password")

        original = b"Secret data"
        encrypted = manager1.encrypt(original)

        from cryptography.fernet import InvalidToken
        with pytest.raises(InvalidToken):
            manager2.decrypt(encrypted)

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting strings."""
        manager = EncryptionManager()
        original = "This is a secret message"

        encrypted = manager.encrypt_string(original)
        decrypted = manager.decrypt_string(encrypted)

        assert isinstance(encrypted, str)
        assert decrypted == original

    def test_encrypt_decrypt_file(self):
        """Test encrypting and decrypting files."""
        manager = EncryptionManager()
        content = b"File content to encrypt"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            input_path = Path(f.name)

        try:
            # Encrypt
            encrypted_path = manager.encrypt_file(input_path)
            assert encrypted_path.exists()
            assert encrypted_path.read_bytes() != content

            # Decrypt
            decrypted_path = manager.decrypt_file(encrypted_path)
            assert decrypted_path.read_bytes() == content

        finally:
            # Cleanup
            input_path.unlink(missing_ok=True)
            encrypted_path.unlink(missing_ok=True)
            decrypted_path.unlink(missing_ok=True)

    def test_verify_encryption(self):
        """Test encryption verification."""
        manager = EncryptionManager()
        original = b"Test data"

        encrypted = manager.encrypt(original)
        assert manager.verify_encryption(encrypted) is True

    def test_verify_encryption_wrong_data(self):
        """Test verification fails for invalid data."""
        manager = EncryptionManager()
        invalid_data = b"This is not encrypted"

        assert manager.verify_encryption(invalid_data) is False

    def test_generate_password(self):
        """Test password generation."""
        password1 = EncryptionManager.generate_password(32)
        password2 = EncryptionManager.generate_password(32)

        assert len(password1) == 32
        assert len(password2) == 32
        assert password1 != password2  # Should be random

    def test_change_password(self):
        """Test re-encrypting data with new password."""
        old_password = "old_pass"
        new_password = "new_pass"
        original = b"Secret data"

        # Encrypt with old password
        old_manager = EncryptionManager(old_password)
        encrypted = old_manager.encrypt(original)

        # Change password
        manager = EncryptionManager()
        re_encrypted = manager.change_password(old_password, new_password, encrypted)

        # Verify new password works
        new_manager = EncryptionManager(new_password)
        decrypted = new_manager.decrypt(re_encrypted)

        assert decrypted == original


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "secure_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to unique salts
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password(self):
        """Test hashing empty password."""
        hashed = hash_password("")
        assert len(hashed) > 0
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        """Test hashing unicode password."""
        password = "пароль123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
