import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.notification import NotificationChannelConfig, NotificationDeliveryLog
from app.models.alert import PrioritizedAlertRecord

logger = logging.getLogger("notification_service")

# In-memory registries for zero-config local development and testing
_MOCK_CONFIGS_REGISTRY: List[NotificationChannelConfig] = [
    NotificationChannelConfig(
        id="cfg-email",
        channel_type="EMAIL",
        config=json.dumps({
            "recipient_email": "operator@chronoshield.ai",
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "allowed_severities": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        }),
        enabled=False
    ),
    NotificationChannelConfig(
        id="cfg-telegram",
        channel_type="TELEGRAM",
        config=json.dumps({
            "bot_token": "MOCK_TELEGRAM_TOKEN",
            "chat_id": "MOCK_CHAT_ID",
            "allowed_severities": ["HIGH", "CRITICAL"]
        }),
        enabled=False
    ),
    NotificationChannelConfig(
        id="cfg-webhook",
        channel_type="WEBHOOK",
        config=json.dumps({
            "webhook_url": "http://localhost:8000/api/v1/notifications/webhook-test",
            "allowed_severities": ["MEDIUM", "HIGH", "CRITICAL"]
        }),
        enabled=False
    )
]

_MOCK_LOGS_REGISTRY: List[NotificationDeliveryLog] = []


class NotificationDeliveryService:
    """
    Core engine managing multi-channel notification rendering, dispatch, retry loops,
    and priority filters.
    """

    @staticmethod
    def render_template(status: str, alert: PrioritizedAlertRecord) -> tuple[str, str]:
        """
        Renders structured title and message templates based on alert state.
        """
        metric = alert.metric_name
        severity = alert.current_severity
        score = alert.priority_score
        description = alert.description
        count = alert.occurrence_count
        time_str = alert.last_occurrence.strftime("%Y-%m-%d %H:%M:%S UTC")

        if status.upper() == "RESOLVED":
            title = f"[ChronoShield AI] RESOLVED: Anomaly on {metric}"
            message = (
                f"### ChronoShield Alert Resolution Report\n\n"
                f"The previously flagged anomaly on **{metric}** has been marked as **RESOLVED**.\n\n"
                f"**Details:**\n"
                f"- **Metric Name:** {metric}\n"
                f"- **Last Severity:** {severity}\n"
                f"- **Priority Score:** {score:.1f}\n"
                f"- **Occurrence Count:** {count}\n"
                f"- **Resolution Time:** {time_str}\n"
                f"- **Description:** {description}\n\n"
                f"Systems are back to nominal operational status."
            )
        elif status.upper() == "ESCALATED":
            title = f"[ChronoShield AI] SLA BREACH & ESCALATION: {metric} ({severity})"
            message = (
                f"### ChronoShield Alert Escalation Report\n\n"
                f"⚠️ **SLA VIOLATION DECLARED** ⚠️\n"
                f"An active anomaly has breached response SLA windows (>30 seconds unacknowledged) and has been escalated.\n\n"
                f"**Details:**\n"
                f"- **Metric Name:** {metric}\n"
                f"- **Current Severity:** {severity}\n"
                f"- **Escalation Priority:** {score:.1f}\n"
                f"- **Escalation Level:** {alert.escalation_level}\n"
                f"- **Total Duplicates:** {count}\n"
                f"- **Breach Time:** {time_str}\n"
                f"- **Operational Context:** {description}"
            )
        else:  # ACTIVE
            title = f"[ChronoShield AI] NEW ALERT: {metric} ({severity})"
            message = (
                f"### ChronoShield Incident Alert Dispatch\n\n"
                f"🚨 **NEW ANOMALY DETECTED** 🚨\n"
                f"A new temporal anomaly has been flagged on **{metric}** and prioritized by the engine.\n\n"
                f"**Details:**\n"
                f"- **Metric Name:** {metric}\n"
                f"- **Assigned Severity:** {severity}\n"
                f"- **Priority Score:** {score:.1f}\n"
                f"- **Incident Count:** {count}\n"
                f"- **Timestamp:** {time_str}\n"
                f"- **Telemetry Context:** {description}"
            )
        return title, message

    @staticmethod
    async def get_channels(db: Optional[AsyncSession]) -> List[NotificationChannelConfig]:
        """Fetch all channel configurations."""
        if db:
            try:
                stmt = select(NotificationChannelConfig)
                res = await db.execute(stmt)
                configs = list(res.scalars().all())
                if configs:
                    return configs
            except Exception as e:
                logger.error(f"PostgreSQL fetch configs failed: {e}. Falling back to in-memory configurations.")
        return _MOCK_CONFIGS_REGISTRY

    @staticmethod
    async def update_channel(
        db: Optional[AsyncSession],
        channel_type: str,
        config_str: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> NotificationChannelConfig:
        """Update a specific channel configuration."""
        target = None
        if db:
            try:
                stmt = select(NotificationChannelConfig).where(NotificationChannelConfig.channel_type == channel_type.upper())
                res = await db.execute(stmt)
                target = res.scalar_one_or_none()
                if target:
                    if config_str is not None:
                        target.config = config_str
                    if enabled is not None:
                        target.enabled = enabled
                    await db.commit()
                    await db.refresh(target)
            except Exception as e:
                await db.rollback()
                logger.error(f"PostgreSQL update config failed for {channel_type}: {e}")

        # Update mock in parallel
        for cfg in _MOCK_CONFIGS_REGISTRY:
            if cfg.channel_type == channel_type.upper():
                if config_str is not None:
                    cfg.config = config_str
                if enabled is not None:
                    cfg.enabled = enabled
                if not target:
                    target = cfg
                break
        
        if not target:
            raise ValueError(f"Channel config '{channel_type}' not found.")
        return target

    @staticmethod
    async def trigger_notifications(
        db: Optional[AsyncSession],
        alert: PrioritizedAlertRecord,
        status_override: Optional[str] = None,
        background_tasks: Optional[Any] = None
    ):
        """
        Checks active channels and dispatches notifications for non-suppressed alerts
        if their severity level matches channel criteria.
        """
        if alert.status == "SUPPRESSED":
            logger.info(f"Skipping notification dispatch for suppressed alert: {alert.id}")
            return

        status = status_override or alert.status
        channels = await NotificationDeliveryService.get_channels(db)
        
        logs_to_add = []
        mock_logs_to_add = []
        for ch in channels:
            if not ch.enabled:
                continue

            try:
                cfg_data = json.loads(ch.config)
            except Exception as e:
                logger.error(f"Failed to parse json config for channel {ch.channel_type}: {e}")
                continue

            allowed_sevs = cfg_data.get("allowed_severities", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            if alert.current_severity.upper() not in [s.upper() for s in allowed_sevs]:
                logger.info(f"Alert {alert.id} severity '{alert.current_severity}' filtered out for channel {ch.channel_type}")
                continue

            # Determine recipient
            recipient = "unknown"
            if ch.channel_type == "EMAIL":
                recipient = cfg_data.get("recipient_email", "ops@chronoshield.ai")
            elif ch.channel_type == "TELEGRAM":
                recipient = cfg_data.get("chat_id", "UnknownChat")
            elif ch.channel_type == "WEBHOOK":
                recipient = cfg_data.get("webhook_url", "http://localhost/webhook")

            title, message = NotificationDeliveryService.render_template(status, alert)

            # Create PENDING delivery log
            log_entry = NotificationDeliveryLog(
                id=f"log-{uuid.uuid4().hex[:8]}",
                alert_id=alert.id,
                channel=ch.channel_type,
                recipient=recipient,
                title=title,
                message=message,
                priority=alert.current_severity,
                status="PENDING",
                retry_count=0,
                max_retries=3,
                error_message=None,
                timestamp=datetime.utcnow()
            )

            if db:
                logs_to_add.append(log_entry)
            else:
                mock_logs_to_add.append(log_entry)

        if db and logs_to_add:
            try:
                for entry in logs_to_add:
                    db.add(entry)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to persist notification delivery logs: {e}")
                for entry in logs_to_add:
                    _MOCK_LOGS_REGISTRY.insert(0, entry)
                logs_to_add = []

        # Dispatch async background execution tasks
        all_logs = logs_to_add if db else mock_logs_to_add
        for entry in all_logs:
            if background_tasks:
                background_tasks.add_task(NotificationDeliveryService.dispatch_log_task, entry.id)
            else:
                asyncio.create_task(NotificationDeliveryService.dispatch_log_task(entry.id))

    @staticmethod
    async def trigger_test_notification(
        db: Optional[AsyncSession],
        channel_type: str,
        recipient: str,
        message: str,
        background_tasks: Optional[Any] = None
    ) -> NotificationDeliveryLog:
        """
        Manually trigger a test notification dispatch for debugging.
        """
        title = "[ChronoShield AI] Dynamic Connectivity Test"
        log_entry = NotificationDeliveryLog(
            id=f"log-{uuid.uuid4().hex[:8]}",
            alert_id=None,
            channel=channel_type.upper(),
            recipient=recipient,
            title=title,
            message=message,
            priority="LOW",
            status="PENDING",
            retry_count=0,
            max_retries=2,
            error_message=None,
            timestamp=datetime.utcnow()
        )

        if db:
            try:
                db.add(log_entry)
                await db.commit()
                await db.refresh(log_entry)
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to persist test notification log: {e}")
                _MOCK_LOGS_REGISTRY.insert(0, log_entry)
        else:
            _MOCK_LOGS_REGISTRY.insert(0, log_entry)

        # Dispatch async background execution task
        if background_tasks:
            background_tasks.add_task(NotificationDeliveryService.dispatch_log_task, log_entry.id)
        else:
            asyncio.create_task(NotificationDeliveryService.dispatch_log_task(log_entry.id))
        return log_entry

    @staticmethod
    async def dispatch_log_task(log_id: str):
        """Task entry point for handling asynchronous dispatches with retries."""
        await NotificationDeliveryService._attempt_dispatch(log_id)

    @staticmethod
    async def _attempt_dispatch(log_id: str):
        """Performs HTTP client request and handles retries under exponential backoff."""
        async with async_session_factory() as session:
            stmt = select(NotificationDeliveryLog).where(NotificationDeliveryLog.id == log_id)
            res = await session.execute(stmt)
            log = res.scalar_one_or_none()

            # Handle mock fallback if DB does not have it
            is_mock = False
            if not log:
                mock_matches = [x for x in _MOCK_LOGS_REGISTRY if x.id == log_id]
                if mock_matches:
                    log = mock_matches[0]
                    is_mock = True
                else:
                    logger.error(f"Notification log ID {log_id} not found in DB or mock store.")
                    return

            try:
                # 1. Dispatching to provider
                if log.channel == "EMAIL":
                    await NotificationDeliveryService._send_email(log.recipient, log.title, log.message)
                elif log.channel == "TELEGRAM":
                    await NotificationDeliveryService._send_telegram(log.recipient, log.title, log.message)
                elif log.channel == "WEBHOOK":
                    await NotificationDeliveryService._send_webhook(log.recipient, log.title, log.message)

                log.status = "SENT"
                log.sent_at = datetime.utcnow()
                log.error_message = None
                
            except Exception as e:
                error_msg = str(e)
                log.retry_count += 1
                log.error_message = error_msg
                logger.warning(f"Notification dispatch failed (attempt {log.retry_count}/{log.max_retries}) for log {log_id}: {error_msg}")

                if log.retry_count < log.max_retries:
                    # Retry with exponential backoff: factor * 2 ** retry_count
                    delay = 1.0 * (2 ** log.retry_count) # e.g. 2s, 4s, 8s
                    asyncio.create_task(NotificationDeliveryService._dispatch_retry_delayed(log_id, delay))
                else:
                    log.status = "FAILED"

            if not is_mock:
                try:
                    await session.commit()
                except Exception as ce:
                    logger.error(f"Failed to commit notification update for log {log_id}: {ce}")
            else:
                # Mock update logs local output
                logger.info(f"Mock Notification log updated. ID: {log.id}, Status: {log.status}, Retries: {log.retry_count}")

    @staticmethod
    async def _dispatch_retry_delayed(log_id: str, delay: float):
        """Sleeps asynchronously and attempts dispatch."""
        await asyncio.sleep(delay)
        await NotificationDeliveryService._attempt_dispatch(log_id)

    # ---------------------------------------------------------------------------
    # Core multi-channel transport protocols
    # ---------------------------------------------------------------------------
    @staticmethod
    async def _send_email(recipient: str, title: str, message: str):
        """Dispatches real SMTP/mail delivery using smtplib."""
        logger.info(f"[TRANSPORT: EMAIL] Routing message to {recipient}. Subject: {title}")
        
        # 1. Fetch channel config to get SMTP settings
        from app.db.session import async_session_factory
        from app.models.notification import NotificationChannelConfig
        
        smtp_host = "localhost"
        smtp_port = 1025
        smtp_username = None
        smtp_password = None
        
        async with async_session_factory() as session:
            try:
                stmt = select(NotificationChannelConfig).where(NotificationChannelConfig.channel_type == "EMAIL")
                res = await session.execute(stmt)
                ch = res.scalar_one_or_none()
                if not ch:
                    # Fallback to mock
                    for cfg in _MOCK_CONFIGS_REGISTRY:
                        if cfg.channel_type == "EMAIL":
                            ch = cfg
                            break
                if ch:
                    cfg_data = json.loads(ch.config)
                    smtp_host = cfg_data.get("smtp_host", smtp_host)
                    smtp_port = int(cfg_data.get("smtp_port", smtp_port))
                    smtp_username = cfg_data.get("smtp_username")
                    smtp_password = cfg_data.get("smtp_password")
            except Exception as e:
                logger.error(f"Failed to load SMTP configs for sending email: {e}")
                # Use in-memory mock fallback
                for cfg in _MOCK_CONFIGS_REGISTRY:
                    if cfg.channel_type == "EMAIL":
                        try:
                            cfg_data = json.loads(cfg.config)
                            smtp_host = cfg_data.get("smtp_host", smtp_host)
                            smtp_port = int(cfg_data.get("smtp_port", smtp_port))
                            smtp_username = cfg_data.get("smtp_username")
                            smtp_password = cfg_data.get("smtp_password")
                        except:
                            pass
                        break

        # If it is localhost/1025 and no credentials exist, bypass real SMTP execution to prevent hanging
        if smtp_host in ("localhost", "127.0.0.1") and smtp_port == 1025 and not smtp_username:
            logger.info(f"[TRANSPORT: EMAIL SIMULATION] Routed successfully to {recipient}")
            await asyncio.sleep(0.1)
            return

        # 2. Build and send MIME email
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Run smtplib blocking calls in an executor to prevent blocking the async loop
        def _sync_send():
            msg = MIMEMultipart()
            msg["From"] = smtp_username or "ops@chronoshield.ai"
            msg["To"] = recipient
            msg["Subject"] = title
            msg.attach(MIMEText(message, "plain"))

            # Start SMTP session
            # If using port 465, use SMTP_SSL. If 587 or other, use standard SMTP with STARTTLS.
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10.0)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10.0)
                # Try to use STARTTLS if supported/necessary (common for 587)
                try:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                except Exception as te:
                    logger.warning(f"STARTTLS negotiation failed or not supported by server: {te}")

            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            server.sendmail(msg["From"], [recipient], msg.as_string())
            server.quit()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_send)
        logger.info(f"[TRANSPORT: EMAIL] Email successfully sent to {recipient}")

    @staticmethod
    async def _send_telegram(chat_id: str, title: str, message: str):
        """Connects to official Telegram bot API endpoints or simulates."""
        # Find config token to check if credentials are populated
        token = "MOCK_TOKEN"
        for cfg in _MOCK_CONFIGS_REGISTRY:
            if cfg.channel_type == "TELEGRAM":
                try:
                    tok = json.loads(cfg.config).get("bot_token", "")
                    if tok and "MOCK" not in tok:
                        token = tok
                except:
                    pass
                break

        if token == "MOCK_TOKEN" or not token:
            logger.info(f"[TRANSPORT: TELEGRAM SIMULATION] ChatID: {chat_id}, Text: {title} - {message[:50]}...")
            await asyncio.sleep(0.1)
            return

        # Real HTTP Telegram call
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"*{title}*\n\n{message}",
            "parse_mode": "Markdown"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise Exception(f"Telegram API responded with status {resp.status_code}: {resp.text}")

    @staticmethod
    async def _send_webhook(webhook_url: str, title: str, message: str):
        """Dispatches outbound HTTP POST containing structural JSON payloads."""
        if "localhost" in webhook_url or "127.0.0.1" in webhook_url or "api/v1/notifications" in webhook_url:
            # Bypass real network dispatch for test loop endpoint URLs
            logger.info(f"[TRANSPORT: WEBHOOK SIMULATION] Dispatched to {webhook_url}")
            await asyncio.sleep(0.1)
            return

        payload = {
            "title": title,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ChronoShield AI"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code not in (200, 201, 202, 204):
                raise Exception(f"Webhook provider returned status {resp.status_code}")

    @staticmethod
    async def get_logs(
        db: Optional[AsyncSession],
        channel: Optional[str] = None,
        status: Optional[str] = None,
        alert_id: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationDeliveryLog]:
        """Fetch delivery audit log records."""
        if db:
            try:
                stmt = select(NotificationDeliveryLog)
                if channel:
                    stmt = stmt.where(NotificationDeliveryLog.channel == channel.upper())
                if status:
                    stmt = stmt.where(NotificationDeliveryLog.status == status.upper())
                if alert_id:
                    stmt = stmt.where(NotificationDeliveryLog.alert_id == alert_id)
                stmt = stmt.order_by(NotificationDeliveryLog.timestamp.desc()).limit(limit)
                
                res = await db.execute(stmt)
                records = list(res.scalars().all())
                if records:
                    return records
            except Exception as e:
                logger.error(f"PostgreSQL query delivery logs failed: {e}")

        # Fallback to mock log registry
        filtered = _MOCK_LOGS_REGISTRY
        if channel:
            filtered = [x for x in filtered if x.channel.upper() == channel.upper()]
        if status:
            filtered = [x for x in filtered if x.status.upper() == status.upper()]
        if alert_id:
            filtered = [x for x in filtered if x.alert_id == alert_id]
        
        return sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]
