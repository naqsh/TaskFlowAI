# Observability — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

## Prompt cache metrics (TF-039)

Exposed on Prometheus `/metrics`:

| Metric | Type | Description |
|---|---|---|
| `prompt_cache_hits_total` | Counter | Responses with `cache_read_tokens > 0` |
| `prompt_cache_misses_total` | Counter | Responses with no cache read |
| `cached_tokens_saved_total` | Counter | Sum of `cache_read_tokens` |
| `prompt_cache_hit_rate` | Gauge | `hits / (hits + misses)` (0 when none) |

### Grafana panel queries

```promql
# Hit rate (target >70% in peak hours)
prompt_cache_hit_rate

# Hits vs misses (5m rate)
rate(prompt_cache_hits_total[5m])
rate(prompt_cache_misses_total[5m])

# Tokens saved
increase(cached_tokens_saved_total[1h])
```

### Cache warming

Background `PromptCacheWarmer` is deferred to MVP 6 (TF-058). Until then, cold starts after idle
are expected; monitor hit rate during active AI usage only.

## Security dwell time SLO (TF-044)

| Metric | Type | Description |
|---|---|---|
| `security_dwell_time_seconds` | Histogram | Incident start → detection latency |
| `blast_radius_score` | Gauge | Per-agent risk score (target <30) |
| `security_violation_detected_total` | Counter | Blocks by scanner layer |
| `dlq_entries_total` | Counter | DLQ events by reason |
| `audit_chain_verification_failures_total` | Counter | Tamper detection failures |

### Grafana alert (dwell time P95)

Rule file: `observability/grafana/security-dwell-time-alert.yaml`

```promql
histogram_quantile(0.95, sum(rate(security_dwell_time_seconds_bucket[5m])) by (le, incident_type)) > 3600
```

Target: P95 dwell time < 1 hour (3600s).
