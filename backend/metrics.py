"""Prometheus metrics definitions."""

from prometheus_client import Counter, Gauge, Histogram

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

RATE_LIMIT_EXCEEDED_TOTAL = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit rejections",
    ["key_type", "path"],
)

# Prompt caching / token metrics (TF-039, MVP 3)
PROMPT_CACHE_HITS_TOTAL = Counter(
    "prompt_cache_hits_total",
    "Total prompt cache hits",
)

PROMPT_CACHE_MISSES_TOTAL = Counter(
    "prompt_cache_misses_total",
    "Total prompt cache misses",
)

CACHED_TOKENS_SAVED_TOTAL = Counter(
    "cached_tokens_saved_total",
    "Estimated prompt-cache tokens saved",
)

PROMPT_CACHE_HIT_RATE = Gauge(
    "prompt_cache_hit_rate",
    "Prompt cache hit rate (hits / (hits + misses))",
)
