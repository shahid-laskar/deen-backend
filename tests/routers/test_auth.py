"""
Auth Router Tests
=================
Tests registration, login, token refresh, logout, and /me endpoint.
"""
import pytest
from httpx import AsyncClient


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@deen.app",
                "password": "Secure123",
                "gender": "male",
                "madhab": "hanafi",
                "timezone": "UTC",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@deen.app"
        assert data["user"]["madhab"] == "hanafi"

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@deen.app",
                "password": "Secure123",
            },
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@deen.app", "password": "short"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_madhab(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid@deen.app",
                "password": "Secure123",
                "madhab": "unknown_school",
            },
        )
        assert resp.status_code == 422

    async def test_register_female_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sister@deen.app",
                "password": "Secure123",
                "gender": "female",
                "madhab": "shafii",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["gender"] == "female"
        assert resp.json()["user"]["madhab"] == "shafii"


class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@deen.app", "password": "TestPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@deen.app"

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@deen.app", "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@deen.app", "password": "TestPass1"},
        )
        assert resp.status_code == 401

    async def test_login_invalid_email_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "TestPass1"},
        )
        assert resp.status_code == 422


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "totally.invalid.token"},
        )
        assert resp.status_code == 401


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@deen.app"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_success(self, client: AsyncClient, auth_headers, registered_user):
        resp = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully."

        # Refresh token should now be revoked
        resp2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp2.status_code == 401
