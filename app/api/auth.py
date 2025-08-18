from fastapi import APIRouter, Depends, status
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLoginResponse, UserLogin
from sqlalchemy.orm import Session
from app.services import auth_service

router = APIRouter()

@router.post(
    "/register", response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED, 
    summary="Register a new user", 
    description="Create a new user in the database"
)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return auth_service.create_user(db=db, user=user)


@router.post(
    "/login", response_model=UserLoginResponse, 
    status_code=status.HTTP_200_OK,
    summary="Login a user", 
    description="Login a user and return a token"
)

def login(user: UserLogin, db: Session = Depends(get_db)):
    print(user)
    return auth_service.login(db=db, user=user) 