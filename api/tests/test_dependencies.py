"""Tests for dependency injection and admin key bootstrapping."""

from api.models.api_key import ApiKey


def test_admin_key_bootstrap(client, db_session):
    """Admin key is auto-created on first use of configured admin key."""
    from api.config import settings

    response = client.get(
        "/health",
    )
    assert response.status_code == 200

    # Use the admin key — should bootstrap
    response = client.get(
        "/v1/models",
        headers={"Authorization": f"Bearer {settings.admin_api_key}"},
    )
    # May fail due to provider, but auth should succeed (not 401)
    # The key should exist in the database now
    admin = db_session.query(ApiKey).filter(ApiKey.key == settings.admin_api_key).first()
    assert admin is not None
    assert admin.is_admin is True
    assert admin.name == "admin"


def test_admin_key_bootstrap_idempotent(client, db_session):
    """Bootstrapping the admin key multiple times doesn't create duplicates."""
    from api.config import settings

    # Use admin key twice
    for _ in range(2):
        client.get(
            "/v1/models",
            headers={"Authorization": f"Bearer {settings.admin_api_key}"},
        )

    count = db_session.query(ApiKey).filter(ApiKey.key == settings.admin_api_key).count()
    assert count == 1
