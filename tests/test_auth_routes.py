VALID_REGISTER = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "password123",
}


def test_register_success(client):
    response = client.post("/auth/register", json=VALID_REGISTER)

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] is not None
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_returns_409(client):
    client.post("/auth/register", json=VALID_REGISTER)

    response = client.post(
        "/auth/register",
        json={**VALID_REGISTER, "username": "alice2"},
    )

    assert response.status_code == 409
    body = response.get_json()
    assert "error" in body
    assert body["field"] == "email"


def test_register_missing_content_type_returns_415(client):
    response = client.post("/auth/register", data="hello")

    assert response.status_code == 415


def test_register_malformed_json_returns_400(client):
    response = client.post(
        "/auth/register", data="{bad", content_type="application/json"
    )

    assert response.status_code == 400


def test_register_empty_object_returns_422(client):
    response = client.post("/auth/register", json={})

    assert response.status_code == 422
    body = response.get_json()
    assert set(body.keys()) == {"error", "message"}


def test_login_success_returns_token_and_user(client):
    client.post("/auth/register", json=VALID_REGISTER)

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["access_token"]
    assert body["user"]["username"] == "alice"
    assert body["user"]["email"] == "alice@example.com"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json=VALID_REGISTER)

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
