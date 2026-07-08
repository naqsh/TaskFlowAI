from __future__ import annotations

from backend.kernel.security_monitor import SecurityMonitor


def test_blast_radius_score_under_normal_load() -> None:
    monitor = SecurityMonitor()
    for _ in range(5):
        monitor.record_execution("context_agent", duration_ms=50, tokens=200, tool_calls=1)
    score = monitor._compute_blast_radius("context_agent")  # noqa: SLF001
    assert score < 30


def test_blast_radius_spikes_on_many_tool_calls() -> None:
    monitor = SecurityMonitor()
    monitor.record_execution("context_agent", duration_ms=100, tokens=500, tool_calls=50)
    score = monitor._compute_blast_radius("context_agent")  # noqa: SLF001
    assert score > 30


def test_blast_radius_capped_at_100() -> None:
    monitor = SecurityMonitor(max_score=100)
    monitor.record_execution("planner_agent", duration_ms=1, tokens=1_000_000, tool_calls=500)
    score = monitor._compute_blast_radius("planner_agent")  # noqa: SLF001
    assert score <= 100


def test_dwell_time_recorded_under_5_seconds() -> None:
    monitor = SecurityMonitor()
    incident_id = "test-incident-1"
    monitor.record_incident_start(incident_id, "injection_attempt")
    dwell = monitor.record_incident_detected(incident_id)
    assert dwell is not None
    assert dwell < 5.0


def test_dwell_time_zero_when_detection_before_start_logged() -> None:
    monitor = SecurityMonitor()
    dwell = monitor.record_incident_detected("missing")
    assert dwell is None


def test_mcp_anomaly_flag_on_size_spike() -> None:
    monitor = SecurityMonitor()
    for size in (100, 110, 105, 95, 100):
        monitor.record_mcp_response("tasks.list", response_size=size, latency_ms=1.0)
    anomaly = monitor.record_mcp_response("tasks.list", response_size=5000, latency_ms=1.0)
    assert anomaly is True
    assert any("mcp_size_anomaly" in f for f in monitor.anomaly_flags)


def test_consensus_disagreement_increments() -> None:
    monitor = SecurityMonitor()
    monitor.record_escalation("planner_agent")
    assert monitor._escalations["planner_agent"] == 1  # noqa: SLF001


def test_monitor_disabled_skips_recording() -> None:
    monitor = SecurityMonitor(enabled=False)
    monitor.record_execution("context_agent", duration_ms=10, tokens=10)
    assert monitor.count == 0
