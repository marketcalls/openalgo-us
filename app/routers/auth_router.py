from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from datetime import timedelta
from fastapi.templating import Jinja2Templates
from typing import Optional
from jose import JWTError, jwt

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    # If user is already logged in, redirect to dashboard
    if access_token:
        try:
            token = access_token.replace("Bearer ", "")
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username = payload.get("sub")
            if username:
                user = db.query(models.User).filter(models.User.username == username).first()
                if user:
                    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        except JWTError:
            pass

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "user": None,
            "is_admin": False,
            "is_superadmin": False
        }
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    # If user is already logged in, redirect to dashboard
    if access_token:
        try:
            token = access_token.replace("Bearer ", "")
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username = payload.get("sub")
            if username:
                user = db.query(models.User).filter(models.User.username == username).first()
                if user:
                    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        except JWTError:
            pass

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "user": None,
            "is_admin": False,
            "is_superadmin": False
        }
    )

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | 
        (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create new user
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    
    # Check if this is the first user (make them superadmin)
    first_user = db.query(models.User).first() is None
    if first_user:
        # Create roles if they don't exist
        roles = ["superadmin", "admin", "user"]
        for role_name in roles:
            db_role = db.query(models.Role).filter(models.Role.name == role_name).first()
            if not db_role:
                db_role = models.Role(name=role_name)
                db.add(db_role)
        db.commit()
        
        # Assign superadmin role to first user
        superadmin_role = db.query(models.Role).filter(models.Role.name == "superadmin").first()
        db_user.role_id = superadmin_role.id
    else:
        # Assign default user role
        user_role = db.query(models.Role).filter(models.Role.name == "user").first()
        db_user.role_id = user_role.id
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutes
        path="/"
    )
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(
        key="access_token",
        path="/"  # Important: must match the path used when setting the cookie
    )
    return response
