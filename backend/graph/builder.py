from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any

from backend.agents.adversarial.node import adversarial_agent_node
from backend.agents.context.node import context_agent_node
from backend.agents.critic.node import critic_agent_node
from backend.agents.orchestrator.node import (
    orchestrator_handle_escalation_node,
    orchestrator_present_node,
)
from backend.agents.planner.node import planner_agent_node
from backend.agents.verification.node import verification_agent_node
from backend.graph.consensus import ConsensusResult, evaluate_consensus
from backend.graph.state import TaskFlowGraphState
from backend.kernel.tool_manager import ToolManager
from backend.llm.router import LLMRouter
from backend.mcp.postgres_stdio import PostgresMCPClient
from backend.mcp.validator import MCPResponseValidator
from backend.security.input_scanner import InputSecurityScanner, SecurityViolationError


@dataclass
class TaskFlowAIGraph:
    llm_router: LLMRouter
    scanner: InputSecurityScanner
    tool_manager: ToolManager
    token_budget_tokens: int = 8000

    async def ainvoke(self, state: TaskFlowGraphState) -> dict[str, Any]:
        """Run the deterministic TaskFlow AI pipeline end-to-end (TF-036)."""

        start = time.perf_counter()
        attempts = 0
        max_attempts = 1  # total additional attempt beyond first

        current_state: TaskFlowGraphState = copy.deepcopy(state)

        while True:
            attempts += 1

            # 1) Input security gate (TF-036).
            try:
                self.scanner.scan_or_raise(current_state["nl_input"])
            except SecurityViolationError as e:
                return {
                    "status": "failure",
                    "trace_id": current_state["trace_id"],
                    "data": {
                        "mode": None,
                        "task_draft": None,
                        "summary": None,
                        "priorities": None,
                    },
                    "metadata": {
                        "trace_id": current_state["trace_id"],
                        "execution_ms": int((time.perf_counter() - start) * 1000),
                        "tokens_used": 0,
                        "model_used": None,
                        "prompt_version": None,
                        "agents_executed": [],
                        "cache_hit_rate": None,
                        "consensus_status": "rejected",
                        "reason": "security_violation_detected",
                        "scan": {
                            "matched_pattern": e.scan.matched_pattern,
                            "confidence": e.scan.confidence,
                        },
                    },
                }

            # 2) Context -> Planner.
            context_env = await context_agent_node(
                current_state,
                tool_manager=self.tool_manager,
            )
            # Planner consumes context if present.
            planner_env = await planner_agent_node(
                current_state,
                self.llm_router,
                scanner=self.scanner,
            )

            # If planner fails hard, route to DLQ.
            if planner_env.status != "success":
                consensus = ConsensusResult(
                    status="rejected",
                    reason=planner_env.escalation.reason or "failure",
                    retry_allowed=False,
                    constraints=None,
                )
                return orchestrator_handle_escalation_node(current_state, consensus=consensus)

            current_state["context_result"] = context_env.result
            current_state["planner_result"] = planner_env.result

            # 3) Verification -> Adversarial -> Critic.
            verification_env = await verification_agent_node(current_state)
            adversarial_env = await adversarial_agent_node(current_state)
            critic_env = await critic_agent_node(current_state, scanner=self.scanner)

            # 4) Consensus.
            consensus = evaluate_consensus(
                verification=verification_env,
                adversarial=adversarial_env,
                critic=critic_env,
                state=current_state,
            )

            # 5) Optional circuit breaker.
            planner_tokens = (
                int(planner_env.metadata.tokens_used)
                if hasattr(planner_env, "metadata") and planner_env.metadata is not None
                else 0
            )
            if planner_tokens > 2 * self.token_budget_tokens:
                dlq_consensus = ConsensusResult(
                    status="rejected",
                    reason="max_retries_exceeded",
                    retry_allowed=False,
                    constraints=None,
                )
                return orchestrator_handle_escalation_node(current_state, consensus=dlq_consensus)

            # 6) Route based on consensus.
            if consensus.status == "agreement":
                return orchestrator_present_node(
                    current_state,
                    planner=planner_env,
                    verification=verification_env,
                    adversarial=adversarial_env,
                    critic=critic_env,
                    consensus=consensus,
                )

            if consensus.retry_allowed and attempts <= max_attempts:
                # TF-036 retry planner once on verification_failed/adversarial major.
                constraints = consensus.constraints or {}
                suffix = ""
                if consensus.reason == "verification_failed" and "concerns" in constraints:
                    suffix = f" Verification concerns: {constraints['concerns']}."
                elif consensus.reason == "adversarial_concerns" and "concerns" in constraints:
                    suffix = f" Adversarial concerns: {constraints['concerns']}."

                # Planner retries should not loop indefinitely; only adjust nl_input.
                current_state = copy.deepcopy(current_state)
                current_state["nl_input"] = f"{state['nl_input']}{suffix}"
                continue

            return orchestrator_handle_escalation_node(current_state, consensus=consensus)


def build_taskflow_ai_graph(
    *,
    llm_router: LLMRouter,
    scanner: InputSecurityScanner | None = None,
    tool_manager: ToolManager | None = None,
    token_budget_tokens: int = 8000,
) -> TaskFlowAIGraph:
    """Factory used by TF-036 and TF-037 (custom minimal graph runner)."""

    resolved_scanner = scanner or InputSecurityScanner()
    resolved_tool_manager = tool_manager
    if resolved_tool_manager is None:
        mcp_client = PostgresMCPClient()
        validator = MCPResponseValidator()
        resolved_tool_manager = ToolManager(mcp_client=mcp_client, validator=validator)

    return TaskFlowAIGraph(
        llm_router=llm_router,
        scanner=resolved_scanner,
        tool_manager=resolved_tool_manager,
        token_budget_tokens=token_budget_tokens,
    )
