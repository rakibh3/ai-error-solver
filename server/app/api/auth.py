from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api import responses as r
from app.core.config import AUTH_RATE_LIMIT
from app.core.database import get_db
from app.core.limiter import client_ip, hit_login_email, limiter
from app.middleware.role_checker import get_current_user
from app.models.user import User
from app.schemas.schemas import ErrorResponse
from app.schemas.user import UserCreate, UserLogin, UserLoginResponse, UserResponse
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    response_description="The newly created account, always with role `USER`.",
    description=(
        "Open registration — anyone may create an account.\n\n"
        "The created account is **always** a regular `USER`. There is no `role` "
        "field on this request, and because unknown fields are rejected rather "
        "than ignored, sending `\"role\": \"ADMIN\"` returns a **422**. "
        "Administrator accounts are provisioned out of band via "
        "`scripts/seed_admin.py`, or granted by an existing admin through "
        "`PATCH /api/v1/admin/users/{user_id}/role`.\n\n"
        "**Password rules:** at least 10 characters, with at least one letter "
        "and one digit."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "An account with this email already exists.",
            "content": {
                "application/json": {
                    "example": {"detail": "User with this email already exists"}
                }
            },
        },
        **r.VALIDATION,
        **r.RATE_LIMITED,
    },
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=client_ip)
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    return auth_service.create_user(db=db, user=user)


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and receive a bearer token",
    response_description="The account plus a JWT bearer token.",
    description=(
        "Authenticate with email and password.\n\n"
        "Send the returned token on every subsequent request as "
        "`Authorization: Bearer <access_token>`. Tokens are valid for 30 days.\n\n"
        "A wrong password, an unknown email, and a deactivated account all "
        "return the same **401**, so the response cannot be used to discover "
        "which emails are registered."
    ),
    responses={
        401: {
            "description": "Wrong password, unknown email, or deactivated account.",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
                }
            },
        },
        **r.VALIDATION,
        **r.RATE_LIMITED,
    },
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=client_ip)
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    if not hit_login_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts for this account. Try again later.",
        )
    return auth_service.login(db=db, credentials=user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out everywhere",
    description=(
        "Revokes **every** token issued to this account so far — on this device "
        "and any other. The token used for this request stops working too; log "
        "in again to get a new one."
    ),
    responses={**r.AUTHENTICATED},
)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.revoke_tokens(db, current_user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated account",
    response_description="The account belonging to the supplied token.",
    description=(
        "Returns the account the bearer token belongs to, including its role. "
        "Use this to decide whether to show administrator features in a client."
    ),
    responses={**r.AUTHENTICATED},
)
def me(current_user: User = Depends(get_current_user)):
    return current_user
