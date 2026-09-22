import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, JWT_SECRET_KEY
from app.core.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def assert_can_access(resource_owner_id: int, current_user: User) -> None:
    """Authorize access to a user-owned resource.

    Call this inside the handler, after loading the row — not as a FastAPI
    dependency. (The previous `require_owner_or_admin` took `resource_owner_id`
    as a plain parameter, so FastAPI would have bound it as a query parameter.)

    Raises 404 rather than 403: a 403 confirms the id exists, which leaks the
    existence of other users' resources to anyone who can guess a UUID.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != resource_owner_id:
        raise HTTPException(status_code=404, detail="Not found")
