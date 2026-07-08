from __future__ import annotations

from uuid import uuid4

import pytest

from backend.memory.episodic import EpisodicMemory
from backend.memory.working import WorkingMemory


@pytest.mark.asyncio
async def test_working_memory_roundtrip() -> None:
    wm = WorkingMemory()
    session_id = "sess-1"
    state = {"nl_input": "hello", "step": 1}

    await wm.set_state(session_id=session_id, state=state)
    loaded = await wm.get_state(session_id=session_id)
    assert loaded == state


@pytest.mark.asyncio
async def test_episodic_memory_isolated_by_user() -> None:
    em = EpisodicMemory()
    user_a = uuid4()
    user_b = uuid4()
    session_id = "ns:wa:sess"

    await em.write_entry(
        user_id=user_a,
        session_id=session_id,
        lesson_type="planner_priorities",
        content={"x": 1},
        version=1,
    )
    await em.write_entry(
        user_id=user_a,
        session_id=session_id,
        lesson_type="planner_priorities",
        content={"x": 2},
        version=2,
    )

    entries_a = await em.read_entries(
        user_id=user_a, session_id=session_id, lesson_type="planner_priorities"
    )
    entries_b = await em.read_entries(
        user_id=user_b, session_id=session_id, lesson_type="planner_priorities"
    )

    assert len(entries_a) == 2
    assert entries_a[-1].content["x"] == 2
    assert entries_b == []
