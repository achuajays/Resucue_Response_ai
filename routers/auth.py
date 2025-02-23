from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User
from schemas import UserCreate, UserLogin
from database import get_db

router = APIRouter()

@router.post("/signup", summary="Create a New User", description="Register a new user with username and password.")
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user by storing their username and plain text password in the database.
    """
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"status": "success", "message": "User created successfully", "username": user.username}

@router.post("/login", summary="User Login", description="Login with username and password.")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user by checking username and plain text password.
    """
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"status": "success", "message": "Login successful", "username": user.username}