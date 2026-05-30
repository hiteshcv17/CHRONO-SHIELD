from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.configs.settings import settings
from app.db.session import get_db_session, get_redis_client
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.auth import get_current_user, require_admin

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Register a new user account with hashed password credentials. (Admin only)
    """
    from app.services.user_service import UserService
    return await UserService.create_user(db, user_in)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client)
):
    """
    Authenticate user, store refresh token session in Redis, set HttpOnly cookie, and return access token.
    """
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        username = form_data.get("username", "")
        password = form_data.get("password", "")
    else:
        try:
            json_data = await request.json()
            username = json_data.get("username", "")
            password = json_data.get("password", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login request body"
            )

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )

    # Fetch user
    stmt = select(User).where(User.username == username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )

    # Tokens
    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)

    payload = decode_token(refresh_token)
    jti = payload.get("jti")

    # Store refresh token in Redis
    redis_key = f"refresh_token:{jti}"
    await redis.set(
        redis_key,
        user.username,
        ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    # Set httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    redis: Redis = Depends(get_redis_client)
):
    """
    Acquire a new access token via HttpOnly refresh token rotation and validation.
    """
    if not refresh_token:
        # Fallback to check request body or headers if cookie isn't sent
        try:
            json_body = await request.json()
            refresh_token = json_body.get("refresh_token")
        except Exception:
            pass

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing"
        )

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    jti = payload.get("jti")
    username = payload.get("sub")
    redis_key = f"refresh_token:{jti}"

    # Verify Redis session
    exists = await redis.exists(redis_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired"
        )

    # Revoke old JTI (Rotation)
    await redis.delete(redis_key)

    # Create new tokens
    new_access_token = create_access_token(username)
    new_refresh_token = create_refresh_token(username)
    new_payload = decode_token(new_refresh_token)
    new_jti = new_payload.get("jti")

    # Store new refresh token in Redis
    await redis.set(
        f"refresh_token:{new_jti}",
        username,
        ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    # Set rotated cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    redis: Redis = Depends(get_redis_client)
):
    """
    Log out active user, revoke the refresh token in Redis, and clear the browser cookie.
    """
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload:
            jti = payload.get("jti")
            # Remove from Redis
            await redis.delete(f"refresh_token:{jti}")

    # Clear cookie
    response.delete_cookie(key="refresh_token")
    return {"success": True, "message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get profile information of the currently authenticated user.
    """
    return current_user
