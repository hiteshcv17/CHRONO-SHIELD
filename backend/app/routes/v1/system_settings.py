from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.db.session import get_db_session, redis_client
from app.models.system_setting import SystemSetting
from app.core.auth import require_admin, require_analyst
from app.core.base import ApiResponse

router = APIRouter()


class SettingsUpdate(BaseModel):
    rate_limiting_enabled: bool = Field(
        ..., description="Whether to enforce API rate limiting policies"
    )


@router.get("", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def get_system_settings(
    db: AsyncSession = Depends(get_db_session), _=Depends(require_analyst)
) -> ApiResponse[dict]:
    """
    Retrieve active general system settings. (Analyst and Admin only)
    """
    try:
        stmt = select(SystemSetting)
        res = await db.execute(stmt)
        settings = res.scalars().all()

        settings_dict = {}
        for s in settings:
            if s.key == "rate_limiting_enabled":
                settings_dict[s.key] = s.value.lower() == "true"
            else:
                settings_dict[s.key] = s.value

        if "rate_limiting_enabled" not in settings_dict:
            settings_dict["rate_limiting_enabled"] = True

        return ApiResponse.ok(settings_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load system settings: {str(e)}",
        )


@router.put("", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def update_system_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(require_admin),
) -> ApiResponse[dict]:
    """
    Modify system settings and sync-flush the Redis settings cache. (Admin only)
    """
    try:
        stmt = select(SystemSetting).where(SystemSetting.key == "rate_limiting_enabled")
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        val_str = "true" if payload.rate_limiting_enabled else "false"

        if record:
            record.value = val_str
        else:
            record = SystemSetting(key="rate_limiting_enabled", value=val_str)
            db.add(record)

        await db.commit()

        try:
            await redis_client.set("settings:rate_limiting_enabled", val_str)
        except Exception:
            pass

        return ApiResponse.ok({"rate_limiting_enabled": payload.rate_limiting_enabled})
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system settings: {str(e)}",
        )
