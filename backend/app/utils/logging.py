import logging
import os
import sys
from datetime import datetime
import json
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """
    Format logs as JSON lines for Loki / ELK log aggregations,
    supporting runtime Correlation IDs and trace properties.
    """

    def __init__(self, service_name: str = "chronoshield-backend"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.module,
            "filename": record.filename,
            "line_number": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }

        # Inject Request Correlation Context if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = getattr(record, "correlation_id")

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Merge extra properties passed
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", logs_dir: str = "./logs") -> None:
    """
    Sets up system-wide dual-stream logger configuration.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clean existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Console Handler (JSON format)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(StructuredJsonFormatter())
    stdout_handler.setLevel(numeric_level)
    root_logger.addHandler(stdout_handler)

    # Local file logger (Standard text format)
    try:
        os.makedirs(logs_dir, exist_ok=True)
        file_path = os.path.join(logs_dir, "backend.log")
        file_handler = logging.FileHandler(file_path, encoding="utf-8")

        file_format = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] [Trace:%(correlation_id)s] - %(message)s",
            defaults={"correlation_id": "SYS"},
        )
        file_handler.setFormatter(file_format)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logger = logging.getLogger("logging_setup")
        logger.warning(f"Could not establish local log files. Reason: {e}")
