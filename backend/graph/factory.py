"""Graph factory with settings-backed security and identity wiring (TF-E4/E5)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.graph.builder import TaskFlowAIGraph, build_taskflow_ai_graph
from backend.kernel.tool_manager import ToolManager
from backend.llm.deterministic import DeterministicPlannerProvider
from backend.llm.local import LocalLLMProvider
from backend.llm.router import LLMRouter
from backend.mcp.postgres_stdio import PostgresMCPClient
from backend.security.factory import (
    build_input_scanner,
    build_mcp_validator,
    build_security_monitor,
)
from backend.security.identity_factory import build_credential_broker, get_nhi_registry
from backend.services.consent_service import ConsentService
from backend.settings import Settings


def build_llm_router(settings: Settings | None = None) -> LLMRouter:
    """LLM router: primary → fallback → optional local provider."""
    resolved = settings or Settings()
    local = None
    if resolved.local_llm_enabled:
        local = LocalLLMProvider(
            base_url=resolved.local_llm_base_url,
            model=resolved.local_llm_model,
            max_context_tokens=resolved.local_llm_max_context_tokens,
        )
    return LLMRouter(
        primary_provider=DeterministicPlannerProvider(),
        fallback_provider=None,
        local_provider=local,
    )


def build_taskflow_graph(
    settings: Settings,
    *,
    session: AsyncSession | None = None,
    llm_router: LLMRouter | None = None,
) -> TaskFlowAIGraph:
    """Build the TaskFlow AI graph with security + identity components."""
    monitor = build_security_monitor(settings)
    scanner = build_input_scanner(settings)
    validator = build_mcp_validator(settings, security_monitor=monitor, session=session)
    nhi = get_nhi_registry()
    credential_broker = build_credential_broker(settings, session=session)
    consent_checker = ConsentService(session) if session is not None else None
    tool_manager = ToolManager(
        mcp_client=PostgresMCPClient(),
        validator=validator,
        nhi_validator=nhi,
        credential_broker=credential_broker,
        consent_checker=consent_checker,
    )
    return build_taskflow_ai_graph(
        llm_router=llm_router or build_llm_router(settings),
        scanner=scanner,
        tool_manager=tool_manager,
        security_monitor=monitor,
    )
