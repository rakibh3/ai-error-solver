from fastapi import Depends, HTTPException, status
from app.api.auth import get_current_user
from app.models.user import User, UserRole

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def role_required(required_role: UserRole):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role {current_user.role} is not permitted to access this resource."
            )
        return current_user
    return role_checker
