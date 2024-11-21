from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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

    # Filter roles based on user permissions
    if not current_user.is_superadmin():
        # Regular admins can only see and assign user role
        roles = [role for role in roles if role.name == "user"]
    
    return templates.TemplateResponse(
        "manage_users.html",
        {
            "request": request,
            "users": users,
            "roles": roles,
            "user": current_user,
            "current_user": current_user,
            "is_admin": current_user.is_admin(),
            "is_superadmin": current_user.is_superadmin()
        }
    )

@router.get("/users", response_model=List[schemas.User])
async def get_users(
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    users = db.query(models.User).all()
    return users

@router.post("/users")
async def create_user(
    user: schemas.UserCreate,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin():
        return JSONResponse(
            status_code=403,
            content={"message": "You don't have permission to create users"}
        )
    
    try:
        # Check if user exists
        db_user = db.query(models.User).filter(
            (models.User.email == user.email) | 
            (models.User.username == user.username)
        ).first()
        if db_user:
            return JSONResponse(
                status_code=400,
                content={"message": "Email or username already registered"}
            )
        
        # Regular admins can only create users with user role
        if not current_user.is_superadmin() and user.role_id != 3:  # 3 is user role
            return JSONResponse(
                status_code=403,
                content={"message": "You can only create users with user role"}
            )
        
        # Create new user
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password,
            role_id=user.role_id
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return JSONResponse(
            status_code=200,
            content={"message": "User created successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin():
        return JSONResponse(
            status_code=403,
            content={"message": "You don't have permission to update users"}
        )
    
    try:
        # Get user to update
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Cannot modify superadmin
        if db_user.is_superadmin():
            return JSONResponse(
                status_code=403,
                content={"message": "Superadmin cannot be modified"}
            )
        
        # Admins cannot change their own role
        if current_user.id == user_id and "role_id" in user_update.dict(exclude_unset=True):
            return JSONResponse(
                status_code=403,
                content={"message": "You cannot change your own role"}
            )
        
        # Regular admins can only update non-admin users
        if not current_user.is_superadmin():
            if db_user.is_admin():
                return JSONResponse(
                    status_code=403,
                    content={"message": "You cannot modify admin users"}
                )
            # Remove role_id from update data if present
            update_data = user_update.dict(exclude_unset=True)
            if "role_id" in update_data:
                del update_data["role_id"]
        else:
            update_data = user_update.dict(exclude_unset=True)
        
        # Update password if provided
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = auth.get_password_hash(update_data.pop("password"))
        
        # Update user fields
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return JSONResponse(
            status_code=200,
            content={"message": "User updated successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin():
        return JSONResponse(
            status_code=403,
            content={"message": "You don't have permission to delete users"}
        )
    
    try:
        # Get user to delete
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Cannot delete superadmin
        if db_user.is_superadmin():
            return JSONResponse(
                status_code=403,
                content={"message": "Superadmin cannot be deleted"}
            )
        
        # Regular admins can only delete non-admin users
        if not current_user.is_superadmin() and db_user.is_admin():
            return JSONResponse(
                status_code=403,
                content={"message": "You cannot delete admin users"}
            )
        
        # Prevent self-deletion
        if db_user.id == current_user.id:
            return JSONResponse(
                status_code=400,
                content={"message": "You cannot delete your own account"}
            )
        
        db.delete(db_user)
        db.commit()
        return JSONResponse(
            status_code=200,
            content={"message": "User deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )
