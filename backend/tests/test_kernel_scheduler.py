import pytest

from backend.kernel.errors import UnknownAgentError
from backend.kernel.scheduler import AgentScheduler


def test_scheduler_unknown_agent_raises() -> None:
    scheduler = AgentScheduler()
    with pytest.raises(UnknownAgentError):
        scheduler.schedule("unknown_agent", priority=1)


def test_scheduler_orders_context_before_planner() -> None:
    scheduler = AgentScheduler()

    # After scheduling context, we only see the first stage.
    groups = scheduler.schedule("context_agent", priority=10)
    assert groups == [["context_agent"]]

    # Adding planner produces [[context_agent], [planner_agent]].
    groups = scheduler.schedule("planner_agent", priority=5)
    assert groups == [["context_agent"], ["planner_agent"]]
