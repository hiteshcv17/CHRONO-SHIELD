from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Alphanumeric username with optional underscores and hyphens",
    )
    email: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        description="Optional valid email address",
    )


class UserRegister(UserBase):
    password: str = Field(
        ..., min_length=6, max_length=100, description="Plaintext password"
    )
    role: Optional[Literal["ADMIN", "ANALYST", "VIEWER"]] = Field(
        "VIEWER", description="Assigned user role"
    )


class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Plaintext password")


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    role: Literal["ADMIN", "ANALYST", "VIEWER"]
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
