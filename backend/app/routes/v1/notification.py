from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.notification import (
    NotificationChannelConfigResponse,
    NotificationChannelConfigUpdate,
    NotificationDeliveryLogResponse,
    NotificationTestPayload,
)
from app.services.notification_service import NotificationDeliveryService
from app.core.auth import require_analyst

router = APIRouter(dependencies=[Depends(require_analyst)])


import json


def mask_secrets(channel_type: str, config_str: str) -> str:
    try:
        data = json.loads(config_str)
        if channel_type.upper() == "EMAIL" and "smtp_password" in data:
            if data["smtp_password"]:
                data["smtp_password"] = "********"
        elif channel_type.upper() == "TELEGRAM" and "bot_token" in data:
            if data["bot_token"]:
                data["bot_token"] = "********"
        return json.dumps(data)
    except Exception:
        return config_str


async def merge_secrets(
    db: AsyncSession, channel_type: str, new_config_str: str
) -> str:
    try:
        new_data = json.loads(new_config_str)
        has_masked_email = (
            channel_type.upper() == "EMAIL"
            and new_data.get("smtp_password") == "********"
        )
        has_masked_tg = (
            channel_type.upper() == "TELEGRAM"
            and new_data.get("bot_token") == "********"
        )

        if has_masked_email or has_masked_tg:
            existing = await NotificationDeliveryService.get_channels(db)
            old_ch = [
                x for x in existing if x.channel_type.upper() == channel_type.upper()
            ]
            if old_ch:
                old_data = json.loads(old_ch[0].config)
                if has_masked_email:
                    new_data["smtp_password"] = old_data.get("smtp_password")
                if has_masked_tg:
                    new_data["bot_token"] = old_data.get("bot_token")
        return json.dumps(new_data)
    except Exception:
        return new_config_str


@router.get(
    "/channels",
    response_model=List[NotificationChannelConfigResponse],
    status_code=status.HTTP_200_OK,
)
async def fetch_channels(
    db: AsyncSession = Depends(get_db_session),
) -> List[NotificationChannelConfigResponse]:
    """
    Retrieve all multi-channel notification configurations with masked credentials.
    """
    configs = await NotificationDeliveryService.get_channels(db)
    masked_configs = []
    for c in configs:
        masked_cfg = NotificationChannelConfigResponse(
            id=c.id,
            channel_type=c.channel_type,
            config=mask_secrets(c.channel_type, c.config),
            enabled=c.enabled,
        )
        masked_configs.append(masked_cfg)
    return masked_configs


@router.put(
    "/channels/{channel_type}",
    response_model=NotificationChannelConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def update_channel_config(
    channel_type: str,
    payload: NotificationChannelConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> NotificationChannelConfigResponse:
    """
    Update credentials, endpoints, or enabled states for a specific channel type while preserving masked secrets.
    """
    try:
        merged_config = await merge_secrets(db, channel_type, payload.config)
        res = await NotificationDeliveryService.update_channel(
            db,
            channel_type=channel_type,
            config_str=merged_config,
            enabled=payload.enabled,
        )
        return NotificationChannelConfigResponse(
            id=res.id,
            channel_type=res.channel_type,
            config=mask_secrets(res.channel_type, res.config),
            enabled=res.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/channels/{channel_type}/test",
    response_model=NotificationDeliveryLogResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_test_dispatch(
    channel_type: str,
    payload: NotificationTestPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> NotificationDeliveryLogResponse:
    """
    Dispatch a test notification to verify credentials/endpoints.
    Creates a pending log record and triggers background transport execution.
    """
    if channel_type.upper() != payload.channel.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel type in path must match payload channel value.",
        )
    return await NotificationDeliveryService.trigger_test_notification(
        db,
        channel_type=channel_type,
        recipient=payload.recipient,
        message=payload.message,
        background_tasks=background_tasks,
    )


@router.get(
    "/logs",
    response_model=List[NotificationDeliveryLogResponse],
    status_code=status.HTTP_200_OK,
)
async def fetch_delivery_logs(
    channel: Optional[str] = Query(
        None, description="Filter logs by channel (EMAIL, TELEGRAM, WEBHOOK)"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter logs by status (PENDING, SENT, FAILED)",
    ),
    alert_id: Optional[str] = Query(
        None, description="Filter logs by associated alert ID"
    ),
    limit: int = Query(50, ge=1, le=200, description="Log retrieve limit"),
    db: AsyncSession = Depends(get_db_session),
) -> List[NotificationDeliveryLogResponse]:
    """
    Fetch historical delivery logs and retry audits.
    """
    return await NotificationDeliveryService.get_logs(
        db, channel=channel, status=status_filter, alert_id=alert_id, limit=limit
    )


@router.post("/webhook-test", status_code=status.HTTP_200_OK)
async def webhook_test_receiver(payload: dict):
    """
    Local mock receiver for verifying webhook deliveries without external dependencies.
    """
    return {"status": "received", "payload_keys": list(payload.keys())}
