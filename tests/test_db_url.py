from backend.app.db import normalize_database_url


def test_render_postgres_url_is_normalized():
    url = "postgres://droneops:secret@db.render.internal:5432/droneops?sslmode=require"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+psycopg2://droneops:secret@")
    assert normalized.endswith("?sslmode=require")


def test_sqlite_url_is_untouched():
    assert normalize_database_url("sqlite:///data/droneops.db") == "sqlite:///data/droneops.db"
