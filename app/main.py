from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from . import models, auth
from .database import engine, init_db, dispose_engine
from .routers import auth_router, user_router, dashboard_router
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
from dotenv import load_dotenv
import json
from typing import Callable, Optional
from contextlib import asynccontextmanager
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from .database import get_db

# Load environment variables
load_dotenv()

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    print("Initializing database...")
    init_db()
    yield
    # Shutdown: Cleanup
    print("Cleaning up...")
    dispose_engine()

# Create FastAPI application
app = FastAPI(
    title=os.getenv("APP_NAME", "OpenAlgo Trading Platform"),
    debug=os.getenv("DEBUG", "False").lower() == "true",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# CORS middleware
allowed_origins = json.loads(os.getenv("ALLOWED_ORIGINS", '["http://localhost:8000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware with secure configuration
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
    same_site=os.getenv("COOKIE_SAMESITE", "lax"),
    https_only=os.getenv("COOKIE_SECURE", "False").lower() == "true"
)

# Root route handler
@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    access_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Try to get access token from cookie
    if not access_token:
        access_token = request.cookies.get("access_token")

    # Try to get user information if logged in
    user = None
    is_admin = False
    is_superadmin = False
    
    if access_token:
        try:
            token = access_token.replace("Bearer ", "")
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username = payload.get("sub")
            if username:
                user = db.query(models.User).filter(models.User.username == username).first()
                if user:
                    user.role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
                    is_admin = user.is_admin()
                    is_superadmin = user.is_superadmin()
        except JWTError:
            pass

    # Always render index.html, but with user info if available
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "is_admin": is_admin,
            "is_superadmin": is_superadmin
        }
    )

# Include routers
app.include_router(auth_router.router, tags=["authentication"])
app.include_router(user_router.router, tags=["users"])
app.include_router(dashboard_router.router, tags=["dashboard"])

# List of paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/login",
    "/register",
    "/token",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/google/login",
    "/auth/google/callback"
]

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Check if the path is public
    if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
        response = await call_next(request)
        return response

    # Get token from cookie
    access_token = request.cookies.get("access_token")
    
    if not access_token or not access_token.startswith("Bearer "):
        # If it's an API request, return JSON response
        if request.headers.get("accept") == "application/json":
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"}
            )
        # Otherwise redirect to login page
        return RedirectResponse(url="/login")

    response = await call_next(request)
    return response

# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        if request.headers.get("accept") == "application/json":
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Page Not Found"},
            status_code=404
        )
    elif exc.status_code == 403:
        if request.headers.get("accept") == "application/json":
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden"}
            )
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Forbidden"},
            status_code=403
        )
    elif exc.status_code == 401:
        if request.headers.get("accept") == "application/json":
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"}
            )
        return RedirectResponse(url="/login")
    return await http_exception_handler(request, exc)

@app.exception_handler(auth.JWTError)
async def jwt_error_handler(request: Request, exc: auth.JWTError):
    if request.headers.get("accept") == "application/json":
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid authentication credentials"}
        )
    return RedirectResponse(url="/login")

@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    if request.headers.get("accept") == "application/json":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Internal Server Error"},
        status_code=500
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "False").lower() == "true",
        workers=int(os.getenv("WORKERS", "1"))
    )
