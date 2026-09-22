import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserLoginResponse,
    UserResponse,
    UserToken,
)

logger = logging.getLogger(__name__)


def create_user(db: Session, user: UserCreate) -> UserResponse:
    """Register a public user.

    The role is hardcoded to USER. This function must never read a role from
    its input — `UserCreate` has no such field, and that is the point.
    """
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    try:
        db_user = User(
            fullname=user.fullname,
            email=user.email,
            password=hash_password(user.password),
            role=UserRole.USER,  # never from the request
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info("User created successfully with email: %s", user.email)
        return UserResponse.model_validate(db_user)

    except IntegrityError as e:
        db.rollback()
        logger.error("Database integrity error while creating user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user due to database constraint",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error while creating user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def login(db: Session, credentials: UserLogin) -> UserLoginResponse:
    # Capture the email before authenticating: the previous version logged
    # `user.email` after rebinding `user` to None, so a wrong password raised
    # AttributeError instead of returning 401.
    email = credentials.email

    user = authenticate_user(db, email, credentials.password)
    if not user:
        logger.warning("Failed login attempt for email: %s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
        access_token = create_access_token(payload)
        logger.info("Successful login for user: %s", user.email)
        return UserLoginResponse(
            user=UserResponse.model_validate(user),
            token=UserToken(access_token=access_token, token_type="bearer"),
        )
    except Exception as e:
        logger.error("Error during login process for %s: %s", email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )


def set_user_role(db: Session, target: User, new_role: UserRole) -> User:
    """Admin-only role change with a last-admin guard."""
    if target.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
        remaining = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != target.id)
            .count()
        )
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the last remaining active admin",
            )

    target.role = new_role
    db.commit()
    db.refresh(target)
    logger.info("Role for user %s changed to %s", target.email, new_role.value)
    return target
