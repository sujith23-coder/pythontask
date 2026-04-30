from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models import Role, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        username=data.username,
        email=str(data.email),
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Bootstrap roles: if no admin exists yet, promote this user to Admin; otherwise default to Viewer.
    admin_exists = (
        db.query(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.name == "Admin")
        .first()
        is not None
    )
    role_name = "Viewer" if admin_exists else "Admin"
    role = db.query(Role).filter(Role.name == role_name).first()
    if role and not db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first():
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()

    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=create_access_token(str(user.id)))
