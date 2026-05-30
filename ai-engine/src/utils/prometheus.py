from prometheus_client import Counter, Histogram

# HTTP request counters & latencies
HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "endpoint"]
)

# AI Anomaly engine specific metrics
ANOMALIES_DETECTED = Counter(
    "anomalies_detected_total",
    "Total anomalies detected by the AI Engine",
    ["metric_name", "severity"]
)

PREPROCESSING_TIME = Histogram(
    "preprocessing_duration_seconds",
    "Time spent on data preprocessing",
    ["step"]
)

MODEL_TRAINING_TIME = Histogram(
    "model_training_duration_seconds",
    "Time spent on training ML models",
    ["model_type"]
)

INGESTION_COUNT = Counter(
    "ingestion_records_processed_total",
    "Total ingestion records processed",
    ["source_type"]
)

INFERENCE_TIME = Histogram(
    "inference_duration_seconds",
    "Time spent on anomaly inference prediction",
    ["model_type"]
)
