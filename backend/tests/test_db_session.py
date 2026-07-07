"""Database session URL preparation tests."""

from backend.db.session import prepare_database_url


def test_prepare_database_url_strips_sslmode_and_sets_ssl_require() -> None:
    url = "postgresql+asyncpg://user:pass@db.example.supabase.co:6543/postgres?sslmode=require"
    clean_url, connect_args = prepare_database_url(url)
    assert "sslmode=" not in clean_url
    assert connect_args["ssl"] == "require"
    assert connect_args["statement_cache_size"] == 0


def test_prepare_database_url_sets_statement_cache_for_supavisor_port() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:6543/taskflow"
    _, connect_args = prepare_database_url(url)
    assert connect_args["statement_cache_size"] == 0


def test_prepare_database_url_preserves_password_special_chars() -> None:
    encoded_password = "p%40ss%23word"
    url = f"postgresql+asyncpg://postgres:{encoded_password}@localhost:5432/taskflow"
    clean_url, connect_args = prepare_database_url(url)
    assert encoded_password in clean_url
    assert connect_args == {}
