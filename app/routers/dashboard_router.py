from fastapi import APIRouter, Depends, Request, HTTPException, Cookie
from sqlalchemy.orm import Session
from .. import models, auth
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
from jose import JWTError, jwt

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

async def get_current_user_from_cookie(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Remove "Bearer " prefix if present
        token = access_token.replace("Bearer ", "")
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Get user's role
    user.role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    
    return user

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "is_admin": current_user.is_admin(),
            "is_superadmin": current_user.is_superadmin()
        }
    )
