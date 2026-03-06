"""Tests for API key management endpoints."""


def test_create_key_as_admin(client, admin_headers):
    """Admin can create new API keys."""
    response = client.post(
        "/v1/keys",
        json={"name": "new-key"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "new-key"
    assert data["key"].startswith("bridge-")
    assert data["is_admin"] is False


def test_create_admin_key(client, admin_headers):
    """Admin can create new admin keys."""
    response = client.post(
        "/v1/keys",
        json={"name": "new-admin", "is_admin": True},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


def test_create_key_as_user(client, user_headers):
    """Non-admin users cannot create keys."""
    response = client.post(
        "/v1/keys",
        json={"name": "should-fail"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_create_key_no_auth(client):
    """Key creation requires authentication."""
    response = client.post("/v1/keys", json={"name": "test"})
    assert response.status_code in (401, 403)


def test_create_key_empty_name(client, admin_headers):
    """Key creation rejects empty names."""
    response = client.post(
        "/v1/keys",
        json={"name": ""},
        headers=admin_headers,
    )
    assert response.status_code == 422
