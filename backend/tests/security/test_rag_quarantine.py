"""Tests for RAG quarantine stub (TF-062)."""

from __future__ import annotations

from backend.memory.quarantine import RAGQuarantineStore


def test_quarantine_and_list() -> None:
    store = RAGQuarantineStore()
    entry = store.quarantine(source_uri="s3://docs/evil.pdf", reason="poisoned embedding")
    assert entry.id
    assert store.is_quarantined("s3://docs/evil.pdf")
    assert len(store.list_quarantined()) == 1


def test_clean_uri_not_quarantined() -> None:
    store = RAGQuarantineStore()
    store.quarantine(source_uri="s3://docs/bad.pdf", reason="test")
    assert not store.is_quarantined("s3://docs/good.pdf")
