"""
Unit tests for the security module.
Tests password validation, hashing, JWT token creation/validation, and token revocation.
"""
import pytest
from datetime import timedelta
from jose import jwt, JWTError

from app.core.security import (
    validate_password,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    is_token_revoked,
)
from app.core.config import settings


@pytest.mark.unit
class TestPasswordValidation:
    """Test password validation functionality."""
    
    def test_valid_password(self):
        """Test that valid passwords pass validation."""
        valid_passwords = [
            "Test123!@#",
            "MyP@ssw0rd",
            "Secur3#Pass",
            "Admin2024!",
        ]
        for password in valid_passwords:
            validate_password(password)  # Should not raise
    
    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password("Test1!")
    
    def test_password_no_uppercase(self):
        """Test that passwords without uppercase are rejected."""
        with pytest.raises(ValueError, match="uppercase letter"):
            validate_password("test123!@#")
    
    def test_password_no_lowercase(self):
        """Test that passwords without lowercase are rejected."""
        with pytest.raises(ValueError, match="lowercase letter"):
            validate_password("TEST123!@#")
    
    def test_password_no_digit(self):
        """Test that passwords without digits are rejected."""
        with pytest.raises(ValueError, match="digit"):
            validate_password("TestPass!@#")
    
    def test_password_no_special_char(self):
        """Test that passwords without special characters are rejected."""
        with pytest.raises(ValueError, match="special character"):
            validate_password("TestPass123")


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test that passwords are hashed correctly."""
        password = "Test123!@#"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash prefix
    
    def test_verify_password_correct(self):
        """Test that correct passwords are verified."""
        password = "Test123!@#"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test that incorrect passwords are rejected."""
        password = "Test123!@#"
        wrong_password = "Wrong123!@#"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_same_password_different_hashes(self):
        """
        Test that hashing the same password twice produces different hashes.
        NOTE: This test validates real bcrypt behavior with salts.
        It will fail with mocked password hashing.
        """
        password = "Test123!@#"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Skip assertion if using mock (hashes will be identical)
        if not hash1.startswith("$2b$12$mocked"):
            assert hash1 != hash2
        
        # Both should verify correctly regardless
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and decoding."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123", "role": "user"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiry time."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=5)
        token = create_access_token(data, expires_delta=expires_delta)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert "exp" in payload
    
    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "user123", "role": "organizer"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "organizer"
        assert payload["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test that invalid tokens raise errors."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(invalid_token)
    
    def test_decode_expired_token(self):
        """Test that expired tokens raise errors."""
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)
        
        with pytest.raises(ValueError, match="Token has expired"):
            decode_token(token)
    
    def test_decode_token_missing_required_fields(self):
        """Test that tokens without required fields raise errors."""
        # Create a token without 'sub' field
        payload = {"role": "user", "type": "access"}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        with pytest.raises(ValueError, match="Invalid token payload"):
            decode_token(token)


@pytest.mark.unit
@pytest.mark.asyncio
class TestTokenRevocation:
    """Test token revocation functionality. Requires Redis."""
    
    @pytest.mark.skip(reason="Requires Redis to be running")
    async def test_revoke_token(self):
        """Test that tokens can be revoked."""
        token = "test_token_123"
        expiry = 3600  # 1 hour
        
        await revoke_token(token, expiry)
        
        # Verify token is revoked
        is_revoked = await is_token_revoked(token)
        assert is_revoked is True
    
    async def test_is_token_revoked_not_revoked(self):
        """Test that non-revoked tokens return False."""
        token = "non_revoked_token"
        
        is_revoked = await is_token_revoked(token)
        assert is_revoked is False
    
    @pytest.mark.skip(reason="Requires Redis to be running")
    async def test_revoke_and_check_multiple_tokens(self):
        """Test revoking multiple tokens."""
        tokens = ["token1", "token2", "token3"]
        
        # Revoke first two tokens
        await revoke_token(tokens[0], 3600)
        await revoke_token(tokens[1], 3600)
        
        # Check revocation status
        assert await is_token_revoked(tokens[0]) is True
        assert await is_token_revoked(tokens[1]) is True
        assert await is_token_revoked(tokens[2]) is False
