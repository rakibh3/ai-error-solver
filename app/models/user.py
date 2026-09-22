import enum

from sqlalchemy import Boolean, Column, Integer, String, Enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """The only two roles in the system.

    There is deliberately no self-service path to ADMIN: see
    `app.schemas.user.UserCreate` (no `role` field, `extra="forbid"`) and
    `app.services.auth_service.create_user` (hardcodes USER).
    """

    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(100), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(
        Enum(UserRole, name="userrole"),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
