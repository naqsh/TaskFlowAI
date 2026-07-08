from __future__ import annotations

import pytest

from backend.security.audit_seal import (
    GENESIS_PREV_HASH,
    AuditLogWriter,
    compute_entry_hash,
    verify_audit_chain,
)


class _FakeAuditRow:
    def __init__(
        self,
        *,
        metadata: dict[str, object],
        prev_hash: str,
        entry_hash: str,
        created_at: object = None,
    ) -> None:
        self.metadata_ = metadata
        self.prev_hash = prev_hash
        self.entry_hash = entry_hash
        self.created_at = created_at


class _FakeResult:
    def __init__(self, rows: list[_FakeAuditRow]) -> None:
        self._rows = rows

    def scalars(self) -> object:
        return self

    def all(self) -> list[_FakeAuditRow]:
        return self._rows


class _FakeSession:
    def __init__(self) -> None:
        self.rows: list[_FakeAuditRow] = []

    async def execute(self, _stmt: object) -> _FakeResult:
        return _FakeResult(self.rows)

    def add(self, row: object) -> None:
        self.rows.append(row)  # type: ignore[arg-type]

    async def flush(self) -> None:
        pass


@pytest.mark.asyncio
async def test_three_entry_chain_verifies() -> None:
    session = _FakeSession()

    prev = GENESIS_PREV_HASH
    for i in range(3):
        meta: dict[str, object] = {"event": f"e{i}"}
        entry_hash = compute_entry_hash(prev, meta)
        session.rows.append(_FakeAuditRow(metadata=meta, prev_hash=prev, entry_hash=entry_hash))
        prev = entry_hash

    assert await verify_audit_chain(session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_tampered_middle_entry_fails_verification() -> None:
    session = _FakeSession()
    meta0: dict[str, object] = {"event": "e0"}
    hash0 = compute_entry_hash(GENESIS_PREV_HASH, meta0)
    meta1: dict[str, object] = {"event": "e1"}
    hash1 = compute_entry_hash(hash0, meta1)
    meta2: dict[str, object] = {"event": "e2-tampered"}
    hash2 = compute_entry_hash(hash1, {"event": "e2"})

    session.rows = [
        _FakeAuditRow(metadata=meta0, prev_hash=GENESIS_PREV_HASH, entry_hash=hash0),
        _FakeAuditRow(metadata=meta1, prev_hash=hash0, entry_hash=hash1),
        _FakeAuditRow(metadata=meta2, prev_hash=hash1, entry_hash=hash2),
    ]
    assert await verify_audit_chain(session) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_empty_chain_verifies_true() -> None:
    session = _FakeSession()
    assert await verify_audit_chain(session) is True  # type: ignore[arg-type]


def test_large_payload_stores_hash_only() -> None:
    big = "x" * 20_000
    sanitized = AuditLogWriter._sanitize_payload({"body": big})
    assert "body_sha256" in sanitized or "payload_sha256" in sanitized
    assert "body" not in sanitized
