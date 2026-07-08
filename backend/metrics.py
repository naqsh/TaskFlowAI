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

# Security metrics (TF-E4, MVP 4)
SECURITY_VIOLATION_DETECTED_TOTAL = Counter(
    "security_violation_detected_total",
    "Total input security violations detected",
    ["layer"],
)

SECURITY_DWELL_TIME_SECONDS = Histogram(
    "security_dwell_time_seconds",
    "Seconds from incident start to detection",
    ["incident_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0),
)

BLAST_RADIUS_SCORE = Gauge(
    "blast_radius_score",
    "Per-agent blast radius score (target <30)",
    ["agent_id"],
)

CONSENSUS_DISAGREEMENT_TOTAL = Counter(
    "consensus_disagreement_total",
    "Total consensus disagreements escalated",
)

DLQ_ENTRIES_TOTAL = Counter(
    "dlq_entries_total",
    "Total DLQ entries created",
    ["reason"],
)

AUDIT_CHAIN_VERIFICATION_FAILURES_TOTAL = Counter(
    "audit_chain_verification_failures_total",
    "Audit hash-chain verification failures",
)
