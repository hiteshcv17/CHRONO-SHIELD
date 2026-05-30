from prometheus_client import Counter, Histogram, Gauge

# HTTP request counters & latencies
HTTP_REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"]
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)

# Active Prioritized Alerts count
ACTIVE_ALERTS = Gauge(
    "active_alerts_count",
    "Number of active prioritized alerts in DB",
    ["severity", "status"],
)

# Cache Hit/Miss operations
CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["prefix", "operation", "status"],
)
