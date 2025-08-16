from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.user import UserRole
from typing import Optional


class UserCreate(BaseModel):
    """Schema for user creation."""
    fullname: str = Field(..., min_length=1, max_length=100, description="Full name of the user")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    role: UserRole = Field(..., description="User role")

class UserLogin(BaseModel):
    """Schema for user login."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserToken(BaseModel):
    """Schema for authentication token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserResponse(BaseModel):
    """Schema for user data response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="User ID")
    fullname: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="User's email address")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether the user account is active")


class UserLoginResponse(BaseModel):
    """Schema for login response containing user data and token."""
    user: UserResponse = Field(..., description="User information")
    token: UserToken = Field(..., description="Authentication token")