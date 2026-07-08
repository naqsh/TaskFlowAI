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
