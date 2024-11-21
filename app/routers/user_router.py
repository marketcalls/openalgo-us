from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List
from .dashboard_router import get_current_user_from_cookie

router = APIRouter(prefix="/manage")
templates = Jinja2Templates(directory="app/templates")

@router.get("/auth", response_class=HTMLResponse)
async def manage_auth_page(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user is superadmin
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access auth settings"
        )
    
    # Get auth settings
    settings = db.query(models.AuthSettings).first()
    if not settings:
        # Create default settings if none exist
        settings = models.AuthSettings(
            regular_auth_enabled=True,
            google_auth_enabled=False,
            updated_by=current_user.id
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return templates.TemplateResponse(
        "manage_auth.html",
        {
            "request": request,
            "settings": settings,
            "user": current_user,
            "is_admin": current_user.is_admin(),
            "is_superadmin": current_user.is_superadmin()
        }
    )

@router.post("/auth", response_class=HTMLResponse)
async def update_auth_settings(
    request: Request,
    regular_auth_enabled: bool = Form(False),
    google_auth_enabled: bool = Form(False),
    google_client_id: str = Form(None),
    google_client_secret: str = Form(None),
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user is superadmin
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can modify auth settings"
        )
    
    # Ensure at least one auth method is enabled
    if not regular_auth_enabled and not google_auth_enabled:
        return templates.TemplateResponse(
            "manage_auth.html",
            {
                "request": request,
                "settings": db.query(models.AuthSettings).first(),
                "user": current_user,
                "is_admin": current_user.is_admin(),
                "is_superadmin": current_user.is_superadmin(),
                "messages": [{"type": "error", "text": "At least one authentication method must be enabled"}]
            }
        )
    
    # If Google auth is enabled, require client ID and secret
    if google_auth_enabled and (not google_client_id or not google_client_secret):
        return templates.TemplateResponse(
            "manage_auth.html",
            {
                "request": request,
                "settings": db.query(models.AuthSettings).first(),
                "user": current_user,
                "is_admin": current_user.is_admin(),
                "is_superadmin": current_user.is_superadmin(),
                "messages": [{"type": "error", "text": "Google Client ID and Secret are required when Google Auth is enabled"}]
            }
        )
    
    # Update settings
    settings = db.query(models.AuthSettings).first()
    if not settings:
        settings = models.AuthSettings()
        db.add(settings)
    
    settings.regular_auth_enabled = regular_auth_enabled
    settings.google_auth_enabled = google_auth_enabled
    settings.google_client_id = google_client_id if google_auth_enabled else None
    settings.google_client_secret = google_client_secret if google_auth_enabled else None
    settings.updated_by = current_user.id
    
    db.commit()
    db.refresh(settings)
    
    return templates.TemplateResponse(
        "manage_auth.html",
        {
            "request": request,
            "settings": settings,
            "user": current_user,
            "is_admin": current_user.is_admin(),
            "is_superadmin": current_user.is_superadmin(),
            "messages": [{"type": "success", "text": "Authentication settings updated successfully"}]
        }
    )

@router.get("", response_class=HTMLResponse)
async def manage_users_page(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user has admin access
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    
    # Get all users and roles
    users = db.query(models.User).all()
    roles = db.query(models.Role).all()

    # Get user's role
    user_role = db.query(models.Role).filter(models.Role.id == current_user.role_id).first()
    
    return templates.TemplateResponse(
        "manage_users.html",
        {
            "request": request,
            "users": users,
            "roles": roles,
            "user": current_user,  # Required for base template
            "current_user": current_user,  # Required for manage_users template
            "is_admin": current_user.is_admin(),  # Required for base template
            "is_superadmin": current_user.is_superadmin()  # Required for base template
        }
    )

@router.get("/users", response_model=List[schemas.User])
async def get_users(
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user has admin access
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    users = db.query(models.User).all()
    return users

@router.post("/users", response_model=schemas.User)
async def create_user(
    user: schemas.UserCreate,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user has admin access
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
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
        hashed_password=hashed_password,
        role_id=3  # Default to user role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user has admin access
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    
    # Get user to update
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying superadmin unless you are superadmin
    if db_user.is_superadmin() and not current_user.is_superadmin():
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can modify other superadmin users"
        )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = auth.get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Check if user has admin access
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    
    # Get user to delete
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting superadmin unless you are superadmin
    if db_user.is_superadmin() and not current_user.is_superadmin():
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can delete superadmin users"
        )
    
    # Prevent self-deletion
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}
