"""Graph factory with settings-backed security wiring (TF-E4)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.graph.builder import TaskFlowAIGraph, build_taskflow_ai_graph
from backend.kernel.tool_manager import ToolManager
from backend.llm.router import LLMRouter
from backend.mcp.postgres_stdio import PostgresMCPClient
from backend.security.factory import (
    build_input_scanner,
    build_mcp_validator,
    build_security_monitor,
)
from backend.settings import Settings


def build_llm_router() -> LLMRouter:
    """Local deterministic LLM router for AI endpoints without external keys."""
    from backend.llm.deterministic import DeterministicPlannerProvider

    return LLMRouter(primary_provider=DeterministicPlannerProvider(), fallback_provider=None)


def build_taskflow_graph(
    settings: Settings,
    *,
    session: AsyncSession | None = None,
    llm_router: LLMRouter | None = None,
) -> TaskFlowAIGraph:
    """Build the TaskFlow AI graph with security components from settings."""
    monitor = build_security_monitor(settings)
    scanner = build_input_scanner(settings)
    validator = build_mcp_validator(settings, security_monitor=monitor, session=session)
    tool_manager = ToolManager(mcp_client=PostgresMCPClient(), validator=validator)
    return build_taskflow_ai_graph(
        llm_router=llm_router or build_llm_router(),
        scanner=scanner,
        tool_manager=tool_manager,
        security_monitor=monitor,
    )
