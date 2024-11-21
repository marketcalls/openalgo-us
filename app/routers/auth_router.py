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
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests
from urllib.parse import urlencode

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Google OAuth 2.0 endpoints
AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
USERINFO_ENDPOINT = 'https://www.googleapis.com/oauth2/v3/userinfo'

async def get_auth_settings(db: Session):
    settings = db.query(models.AuthSettings).first()
    if not settings:
        settings = models.AuthSettings(
            regular_auth_enabled=True,
            google_auth_enabled=False
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

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

    # Get auth settings
    settings = await get_auth_settings(db)
    
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "user": None,
            "is_admin": False,
            "is_superadmin": False,
            "regular_auth_enabled": settings.regular_auth_enabled,
            "google_auth_enabled": settings.google_auth_enabled,
            "google_client_id": settings.google_client_id if settings.google_auth_enabled else None
        }
    )

@router.get("/auth/google/login")
async def google_login(
    request: Request,
    db: Session = Depends(get_db)
):
    # Check if Google auth is enabled
    settings = await get_auth_settings(db)
    if not settings.google_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google authentication is disabled"
        )

    # Construct the callback URL
    callback_url = str(request.base_url)[:-1] + "/auth/google/callback"

    # Google OAuth configuration
    params = {
        'client_id': settings.google_client_id,
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    # Redirect to Google's OAuth page
    return RedirectResponse(
        f'{AUTHORIZATION_ENDPOINT}?{urlencode(params)}'
    )

@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    # Check if Google auth is enabled
    settings = await get_auth_settings(db)
    if not settings.google_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google authentication is disabled"
        )

    try:
        # Construct the callback URL
        callback_url = str(request.base_url)[:-1] + "/auth/google/callback"

        # Exchange authorization code for tokens
        token_response = requests.post(
            TOKEN_ENDPOINT,
            data={
                'code': code,
                'client_id': settings.google_client_id,
                'client_secret': settings.google_client_secret,
                'redirect_uri': callback_url,
                'grant_type': 'authorization_code'
            }
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            token_data['id_token'],
            google_requests.Request(),
            settings.google_client_id
        )

        # Get user info
        user_info_response = requests.get(
            USERINFO_ENDPOINT,
            headers={'Authorization': f'Bearer {token_data["access_token"]}'}
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        # Check if user exists
        user = db.query(models.User).filter(models.User.email == user_info['email']).first()
        if not user:
            # Create new user
            username = user_info['email'].split('@')[0]
            base_username = username
            counter = 1
            while db.query(models.User).filter(models.User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1

            # Get default role
            user_role = db.query(models.Role).filter(models.Role.name == "user").first()
            if not user_role:
                user_role = models.Role(name="user")
                db.add(user_role)
                db.commit()

            user = models.User(
                email=user_info['email'],
                username=username,
                hashed_password="",  # No password for Google auth users
                role_id=user_role.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create access token
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

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate with Google: {str(e)}"
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

    # Get auth settings
    settings = await get_auth_settings(db)
    if not settings.regular_auth_enabled:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

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
    # Check if regular auth is enabled
    settings = await get_auth_settings(db)
    if not settings.regular_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Regular authentication is disabled"
        )

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
async def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    # Check if regular auth is enabled
    settings = await get_auth_settings(db)
    if not settings.regular_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Regular authentication is disabled"
        )

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
    # Check if regular auth is enabled
    settings = await get_auth_settings(db)
    if not settings.regular_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Regular authentication is disabled"
        )

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
