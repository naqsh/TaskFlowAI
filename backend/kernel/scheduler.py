from __future__ import annotations

from collections.abc import Sequence

from backend.kernel.errors import UnknownAgentError


class AgentScheduler:
    """Stage-aware scheduler for multi-agent execution.

    In Part 1 we only enforce the initial ordering:
    - `context_agent` must run before `planner_agent`
    """

    _stage_order: list[str] = [
        "context_agent",
        "planner_agent",
    ]

    def __init__(self, known_agents: Sequence[str] | None = None) -> None:
        self._known_agents = (
            set(known_agents) if known_agents is not None else set(self._stage_order)
        )
        self._priorities: dict[str, int] = {}

    def schedule(self, agent_id: str, priority: int) -> list[list[str]]:
        if agent_id not in self._known_agents:
            raise UnknownAgentError(f"unknown agent_id={agent_id}")

        self._priorities[agent_id] = priority
        return self.execution_groups()

    def execution_groups(self) -> list[list[str]]:
        """Return parallel execution groups based on known stage order."""
        groups: list[list[str]] = []

        for stage in self._stage_order:
            in_stage = [a for a in self._priorities if a == stage]
            if not in_stage:
                continue

            # Stage is deterministic (single-agent) in Part 1; preserve priority sorting anyway.
            sorted_stage = sorted(in_stage, key=lambda a: self._priorities.get(a, 0), reverse=True)
            groups.append(sorted_stage)

        # If both context_agent and planner_agent were added, we expect:
        #   [[context_agent], [planner_agent]]
        return groups
