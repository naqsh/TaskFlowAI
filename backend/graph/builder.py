from __future__ import annotations

import copy
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
from backend.graph.dlq_handler import dlq_handler_node
from backend.graph.state import TaskFlowGraphState
from backend.kernel.security_monitor import SecurityMonitor
from backend.kernel.tool_manager import ToolManager
from backend.llm.router import LLMRouter
from backend.mcp.postgres_stdio import PostgresMCPClient
from backend.schemas.envelope import AgentResultEnvelope
from backend.security.input_scanner import InputSecurityScanner, SecurityViolationError


@dataclass
class TaskFlowAIGraph:
    llm_router: LLMRouter
    scanner: InputSecurityScanner
    tool_manager: ToolManager
    security_monitor: SecurityMonitor | None = None
    token_budget_tokens: int = 8000

    async def ainvoke(self, state: TaskFlowGraphState) -> dict[str, Any]:
        """Run the deterministic TaskFlow AI pipeline end-to-end (TF-036)."""

        attempts = 0
        max_attempts = 1  # total additional attempt beyond first

        current_state: TaskFlowGraphState = copy.deepcopy(state)

        while True:
            attempts += 1

            # 1) Input security gate (TF-036 / TF-041).
            incident_id = f"{current_state['trace_id']}:input"
            if self.security_monitor is not None:
                self.security_monitor.record_incident_start(incident_id, "injection_attempt")
            try:
                session_key = f"{current_state.get('user_id')}:{current_state.get('workspace_id')}"
                self.scanner.scan_or_raise(
                    current_state["nl_input"],
                    session_key=session_key if current_state.get("user_id") else None,
                )
            except SecurityViolationError as e:
                if self.security_monitor is not None:
                    self.security_monitor.record_incident_detected(incident_id)
                return dlq_handler_node(
                    reason="security_violation_detected",
                    envelope={
                        "matched_pattern": e.scan.matched_pattern,
                        "confidence": e.scan.confidence,
                        "layer": e.scan.layer,
                    },
                    trace_id=current_state["trace_id"],
                )

            # 2) Context -> Planner.
            context_env = await context_agent_node(
                current_state,
                tool_manager=self.tool_manager,
            )
            self._record_agent_execution(context_env, tool_calls=3)

            # Planner consumes context if present.
            planner_env = await planner_agent_node(
                current_state,
                self.llm_router,
                scanner=self.scanner,
            )
            self._record_agent_execution(planner_env)

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
            self._record_agent_execution(verification_env)
            adversarial_env = await adversarial_agent_node(current_state)
            self._record_agent_execution(adversarial_env)
            critic_env = await critic_agent_node(current_state, scanner=self.scanner)
            self._record_agent_execution(critic_env)

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

    def _record_agent_execution(
        self, envelope: AgentResultEnvelope, *, tool_calls: int = 0
    ) -> None:
        if self.security_monitor is None:
            return
        self.security_monitor.record_execution(
            envelope.agent_id,
            envelope.metadata.execution_ms,
            envelope.metadata.tokens_used,
            tool_calls=tool_calls,
        )
        if envelope.status == "escalated":
            self.security_monitor.record_escalation(envelope.agent_id)


def build_taskflow_ai_graph(
    *,
    llm_router: LLMRouter,
    scanner: InputSecurityScanner | None = None,
    tool_manager: ToolManager | None = None,
    security_monitor: SecurityMonitor | None = None,
    token_budget_tokens: int = 8000,
) -> TaskFlowAIGraph:
    """Factory used by TF-036 and TF-037 (custom minimal graph runner)."""

    from backend.security.factory import (
        build_input_scanner,
        build_mcp_validator,
        build_security_monitor,
    )
    from backend.settings import get_settings

    settings = get_settings()
    resolved_monitor = security_monitor or build_security_monitor(settings)
    resolved_scanner = scanner or build_input_scanner(settings)
    resolved_tool_manager = tool_manager
    if resolved_tool_manager is None:
        mcp_client = PostgresMCPClient()
        validator = build_mcp_validator(settings, security_monitor=resolved_monitor)
        resolved_tool_manager = ToolManager(mcp_client=mcp_client, validator=validator)

    return TaskFlowAIGraph(
        llm_router=llm_router,
        scanner=resolved_scanner,
        tool_manager=resolved_tool_manager,
        security_monitor=resolved_monitor,
        token_budget_tokens=token_budget_tokens,
    )
