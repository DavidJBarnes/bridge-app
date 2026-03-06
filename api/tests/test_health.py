"""Tests for the health check endpoint."""


def test_health_check(client):
    """Health check returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
