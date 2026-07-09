from __future__ import annotations


class KernelError(Exception):
    """Base error for kernel runtime issues."""


class UnknownAgentError(KernelError):
    """Raised when an unknown agent_id is referenced."""


class MCPTimeoutError(KernelError):
    """Raised when an MCP tool call times out."""


class ToolNotAllowedError(KernelError):
    """Raised when a tool is not present in an agent allowlist."""


class ToolChainLimitExceeded(KernelError):
    """Raised when a tool-call chain exceeds the maximum allowed steps."""


class MCPValidationError(KernelError):
    """Raised when MCP responses fail schema validation."""


class ConfusedDeputyError(KernelError):
    """Raised when agent delegation intent mismatches MCP tool."""


class AgentIdentityError(KernelError):
    """Raised when NHI agent certificate validation fails."""
