"""
tests/test_health.py

Sample unit/integration test covering the Health Check blueprint
(Section 9/12). Demonstrates the pattern every future test module
follows: use the `client` fixture, assert on status code + envelope shape.
"""


def test_health_endpoint_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "alive"


def test_status_endpoint_reports_database_connected(client):
    response = client.get("/status")
    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["database"] == "connected"
