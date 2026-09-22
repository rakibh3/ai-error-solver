import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole

_PASSWORD_MIN = 10


class UserCreate(BaseModel):
    """Public registration payload.

    There is deliberately NO `role` field, and `extra="forbid"` means a client
    that sends `{"role": "ADMIN"}` gets a 422 rather than having it silently
    dropped. Admin is granted only by scripts/seed_admin.py or by an existing
    admin via PATCH /api/v1/admin/users/{id}/role.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "fullname": "Ayesha Rahman",
                    "email": "ayesha@example.com",
                    "password": "Str0ngPassw0rd",
                }
            ]
        },
    )

    fullname: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The user's display name. Leading and trailing whitespace is stripped.",
        examples=["Ayesha Rahman"],
    )
    email: EmailStr = Field(
        ...,
        description="A valid email address. Used as the login identifier and must be unique.",
        examples=["ayesha@example.com"],
    )
    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN,
        max_length=128,
        description=(
            f"At least {_PASSWORD_MIN} characters, containing at least one letter "
            "and one digit."
        ),
        examples=["Str0ngPassw0rd"],
    )

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one digit")
        return v

    @field_validator("fullname")
    @classmethod
    def fullname_not_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Full name cannot be blank")
        return cleaned


class UserLogin(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "ayesha@example.com", "password": "Str0ngPassw0rd"}
            ]
        }
    )

    email: EmailStr = Field(
        ..., description="The email used at registration.", examples=["ayesha@example.com"]
    )
    password: str = Field(
        ..., description="The account password.", examples=["Str0ngPassw0rd"]
    )


class UserToken(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiJ9.abc123",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str = Field(
        ...,
        description="JWT bearer token. Send as `Authorization: Bearer <token>`.",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiI0MiIsImVtYWlsIjoiYXllc2hhQGV4YW1wbGUuY29tIn0."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ],
    )
    token_type: str = Field(
        default="bearer", description="Always `bearer`.", examples=["bearer"]
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 42,
                    "fullname": "Ayesha Rahman",
                    "email": "ayesha@example.com",
                    "role": "USER",
                    "is_active": True,
                }
            ]
        },
    )

    id: int = Field(..., description="Internal user id.", examples=[42])
    fullname: str = Field(..., examples=["Ayesha Rahman"])
    email: EmailStr = Field(..., examples=["ayesha@example.com"])
    role: UserRole = Field(
        ...,
        description=(
            "`USER` for every account created through registration. `ADMIN` can "
            "only be set by the seed script or by another admin."
        ),
        examples=["USER"],
    )
    is_active: bool = Field(
        ...,
        description="Inactive accounts cannot log in.",
        examples=[True],
    )


class UserLoginResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user": {
                        "id": 42,
                        "fullname": "Ayesha Rahman",
                        "email": "ayesha@example.com",
                        "role": "USER",
                        "is_active": True,
                    },
                    "token": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiJ9.abc123",
                        "token_type": "bearer",
                    },
                }
            ]
        }
    )

    user: UserResponse
    token: UserToken


class RoleUpdateRequest(BaseModel):
    """Admin-only role change. Separate from UserCreate on purpose."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"role": "ADMIN"}, {"role": "USER"}]},
    )

    role: UserRole = Field(
        ...,
        description=(
            "The new role. Demoting the last remaining active admin is refused "
            "with a 409."
        ),
        examples=["ADMIN"],
    )
