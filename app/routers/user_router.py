from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List
from .dashboard_router import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/manage", response_class=HTMLResponse)
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
