"""Prometheus metrics definitions."""

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "path"],
)
