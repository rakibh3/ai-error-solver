import bcrypt
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# bcrypt is called directly: passlib is unmaintained and breaks against
# bcrypt>=4.1 (every hash raised, so registration and login returned 500).
# Hashes stay standard `$2b$` strings, so rows written via passlib still verify.
BCRYPT_ROUNDS = 12

# bcrypt only reads the first 72 bytes; bcrypt>=5 raises instead of silently
# truncating. Truncate explicitly so hashes created by passlib (which truncated)
# keep verifying for passwords longer than that.
_BCRYPT_MAX_BYTES = 72

logger = logging.getLogger(__name__)


def _bcrypt_input(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        str: Hashed password
        
    Raises:
        ValueError: If password is empty or None
    """
    if not password or not password.strip():
        raise ValueError("Password cannot be empty")
    
    try:
        return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("ascii")
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise ValueError("Failed to hash password")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        bool: True if the passwords match, False otherwise

    Raises:
        ValueError: If hashed_password is empty or None
    """
    if not hashed_password or not hashed_password.strip():
        raise ValueError("Hashed password cannot be empty")

    try:
        return bcrypt.checkpw(_bcrypt_input(plain_password), hashed_password.encode("ascii"))
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False



def create_access_token(data: dict, expires_in: Optional[timedelta] = None):
    """
    Create an access token using JWT.
    
    Args:
        data: Data to include in the token payload
        expires_in: Optional timedelta for token expiration
        
    Returns:
        str: JWT access token
        
    Raises:
        ValueError: If data is empty or None
    """
    if not data:
        raise ValueError("Data cannot be empty")

    try:
        payload = data.copy()

        if expires_in:
            expire = datetime.now(timezone.utc) + expires_in
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload.update({"exp": expire})
        
        encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created successfully for user: {data.get('email')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise ValueError("Failed to create access token")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT access token.
    
    Args:
        token: JWT access token to verify
        
    Returns:
        Optional[Dict[str, Any]]: Token payload if verification successful, None otherwise
    """
    if not token:
        raise ValueError("Token cannot be empty")

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise ValueError("Invalid token")

