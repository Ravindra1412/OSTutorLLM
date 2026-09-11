"""
tests/test_auth.py

Covers the one blueprint with real logic in this phase: registration,
login, duplicate-email rejection, and the login-required /me endpoint.
"""


def register_payload(email="jordan@example.com"):
    return {
        "name": "Jordan Smith",
        "email": email,
        "password": "supersecret123",
        "role": "student",
    }


def test_register_creates_user(client):
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["email"] == "jordan@example.com"
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json=register_payload())
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 409
    assert response.get_json()["status"] == "fail"


def test_login_with_correct_credentials_succeeds(client):
    client.post("/api/auth/register", json=register_payload())
    response = client.post(
        "/api/auth/login", json={"email": "jordan@example.com", "password": "supersecret123"}
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_login_with_wrong_password_fails(client):
    client.post("/api/auth/register", json=register_payload())
    response = client.post(
        "/api/auth/login", json={"email": "jordan@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.get_json()["status"] == "fail"


def test_me_endpoint_requires_login(client):
    response = client.get("/api/auth/me")
    # Flask-Login redirects unauthenticated users by default (302) unless
    # configured otherwise; either a redirect or a 401 indicates protection is active.
    assert response.status_code in (302, 401)


def test_full_register_login_me_flow(client):
    client.post("/api/auth/register", json=register_payload())
    client.post("/api/auth/login", json={"email": "jordan@example.com", "password": "supersecret123"})
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.get_json()["data"]["email"] == "jordan@example.com"
