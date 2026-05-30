from enum import Enum, IntEnum


class CacheTTL(IntEnum):
    ANOMALIES = 30
    ASSETS = 60
    HEALTH = 30
    FORECASTING = 120
    CORRELATION = 60
    EXPLAIN = 300
    DEFAULT = 60



class SeverityWeight(float, Enum):
    CRITICAL = 40.0
    HIGH = 25.0
    MEDIUM = 12.0
    LOW = 5.0
    
    @classmethod
    def get_weight(cls, severity: str) -> float:
        try:
            return cls[severity.upper()].value
        except KeyError:
            return cls.LOW.value


class AlertConstants(IntEnum):
    COOLDOWN_SECONDS = 120
    SLA_ESCALATION_SECONDS = 30


class PaginationDefaults(IntEnum):
    PAGE = 1
    PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"
