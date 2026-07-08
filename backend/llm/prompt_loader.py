from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

AgentName = Literal["context", "planner", "verification", "adversarial", "critic", "orchestrator"]

REQUIRED_PROMPT_FILES: tuple[str, ...] = (
    "system.md",
    "context.md",
    "instructions.md",
    "examples.md",
    "output-schema.md",
    "tools.md",
    "reasoning.md",
    "guardrails.md",
    "input-security.md",
    "quality-checklist.md",
    "CHANGELOG.md",
    "CONTRACT.md",
)


@dataclass(frozen=True)
class AgentPromptPack:
    agent: AgentName
    system: str
    context: str
    instructions: str
    examples: str
    output_schema: str
    tools: str
    reasoning: str
    guardrails: str
    input_security: str
    quality_checklist: str
    changelog: str
    contract: str
    version: str = "v2.0.0"

    def assemble_system_blocks(self) -> list[dict[str, str]]:
        """Cache-friendly ordering: stable prompts first, dynamic content last (TF-038/TF-039).

        Whitespace in these blocks is significant for OpenAI prefix caching — do not trim
        or reformat after load (documented in prompts/AGENT.md).
        """

        return [
            {"role": "system", "content": self.system},
            {"role": "system", "content": self.guardrails},
            {"role": "system", "content": self.input_security},
            {"role": "system", "content": self.instructions},
            {"role": "system", "content": self.examples},
            {"role": "system", "content": self.output_schema},
            {"role": "system", "content": f"prompt_version={self.version}"},
        ]


class PromptLoaderError(RuntimeError):
    pass


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as e:
        raise PromptLoaderError(f"missing prompt file: {path}") from e


def _prompts_root(prompts_root: str | None, agent: AgentName) -> str:
    if prompts_root is not None:
        return prompts_root if prompts_root.endswith(agent) else os.path.join(prompts_root, agent)
    return os.path.join(os.getcwd(), "prompts", agent)


def validate_agent_prompt_pack(
    agent: AgentName,
    *,
    prompts_root: str | None = None,
) -> list[str]:
    """Return missing required files (empty list = valid). Fail-fast helper for startup/CI."""

    root = _prompts_root(prompts_root, agent)
    missing: list[str] = []
    for name in REQUIRED_PROMPT_FILES:
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            missing.append(path)
    return missing


def assert_all_prompt_packs(*, prompts_root: str | None = None) -> None:
    """Fail fast at startup when any of the 6 agent packs is incomplete (TF-038)."""

    agents: tuple[AgentName, ...] = (
        "context",
        "planner",
        "verification",
        "adversarial",
        "critic",
        "orchestrator",
    )
    missing_all: list[str] = []
    for agent in agents:
        missing_all.extend(validate_agent_prompt_pack(agent, prompts_root=prompts_root))
    if missing_all:
        raise PromptLoaderError("missing prompt files at startup: " + ", ".join(missing_all[:12]))


@lru_cache(maxsize=12)
def _load_cached(agent: AgentName, root: str) -> AgentPromptPack:
    files = {name: _read_file(os.path.join(root, name)) for name in REQUIRED_PROMPT_FILES}
    examples = files["examples.md"]
    thinking_count = examples.count("<thinking>")
    if thinking_count < 3:
        raise PromptLoaderError(
            f"{agent} examples.md requires >=3 <thinking> blocks, found {thinking_count}"
        )
    if (
        "max_tokens" not in files["CONTRACT.md"].lower()
        and "Token budget" not in files["CONTRACT.md"]
    ):
        raise PromptLoaderError(f"{agent} CONTRACT.md must specify max_tokens / token budget")

    return AgentPromptPack(
        agent=agent,
        system=files["system.md"],
        context=files["context.md"],
        instructions=files["instructions.md"],
        examples=files["examples.md"],
        output_schema=files["output-schema.md"],
        tools=files["tools.md"],
        reasoning=files["reasoning.md"],
        guardrails=files["guardrails.md"],
        input_security=files["input-security.md"],
        quality_checklist=files["quality-checklist.md"],
        changelog=files["CHANGELOG.md"],
        contract=files["CONTRACT.md"],
        version="v2.0.0",
    )


def load_agent_prompt_pack(
    agent: AgentName,
    *,
    prompts_root: str | None = None,
) -> AgentPromptPack:
    """Load a complete v2.0.0 prompt pack (11 files + CONTRACT) for the given agent."""

    root = _prompts_root(prompts_root, agent)
    missing = validate_agent_prompt_pack(agent, prompts_root=prompts_root)
    if missing:
        raise PromptLoaderError(f"missing prompt file: {missing[0]}")
    return _load_cached(agent, root)
