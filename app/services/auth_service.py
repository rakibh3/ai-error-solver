from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.schemas.user import UserCreate, UserToken, UserLoginResponse, UserResponse
from app.core.security import create_access_token, verify_password, hash_password
from fastapi import HTTPException, status
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_user(db: Session, user: UserCreate) -> UserResponse:
    """
    Create a new user in the database.
    
    Args:
        db: Database session
        user: User creation data
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If user with email already exists
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    try:
        hashed_password = hash_password(user.password)
        db_user = User(
            fullname=user.fullname,
            email=user.email,
            password=hashed_password,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User created successfully with email: {user.email}")
        return UserResponse.model_validate(db_user)
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user due to database constraint"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by email address.
    
    Args:
        db: Database session
        email: User's email address
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    try:
        return db.query(User).filter(User.email == email).first()
    except Exception as e:
        logger.error(f"Error retrieving user by email {email}: {e}")
        return None


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieve a user by ID.
    
    Args:
        db: Database session
        user_id: User's ID
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    try:
        return db.query(User).filter(User.id == user_id).first()
    except Exception as e:
        logger.error(f"Error retrieving user by ID {user_id}: {e}")
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.
    
    Args:
        db: Database session
        email: User's email
        password: Plain text password
        
    Returns:
        Optional[User]: User object if authentication successful, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    if not user.is_active:
        return None
        
    if not verify_password(password, user.password):
        return None
        
    return user


def login(db: Session, email: str, password: str) -> UserLoginResponse:
    """
    Authenticate user and return login response with user data and token.
    
    Args:
        db: Database session
        email: User's email
        password: Plain text password
        
    Returns:
        UserLoginResponse: User data and authentication token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(db, email, password)
    if not user:
        logger.warning(f"Failed login attempt for email: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Create token payload
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        
        access_token = create_access_token(payload)
        user_response = UserResponse.model_validate(user)
        token = UserToken(access_token=access_token, token_type="bearer")
        
        logger.info(f"Successful login for user: {email}")
        return UserLoginResponse(user=user_response, token=token)
        
    except Exception as e:
        logger.error(f"Error during login process for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )