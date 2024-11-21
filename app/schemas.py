from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None

class User(UserBase):
    id: int
    is_active: bool
    role_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginForm(BaseModel):
    username: str
    password: str

class AuthSettingsBase(BaseModel):
    regular_auth_enabled: bool
    google_auth_enabled: bool
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

class AuthSettingsCreate(AuthSettingsBase):
    pass

class AuthSettingsUpdate(BaseModel):
    regular_auth_enabled: Optional[bool] = None
    google_auth_enabled: Optional[bool] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

class AuthSettings(AuthSettingsBase):
    id: int
    updated_at: Optional[datetime] = None
    updated_by: int

    class Config:
        from_attributes = True
