import jwt
import logging
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10
)

logger = logging.getLogger(__name__)


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
        return pwd_context.hash(password)
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
        return pwd_context.verify(plain_password, hashed_password)
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

