import pytest
from httpx import AsyncClient


async def register_user(async_client: AsyncClient,
                        email: str,
                        password: str,
                        ):

    return await async_client.post(
        "/register", json={"email": email, "password": password}
    )


@pytest.mark.anyio
async def test_register_user(async_client: AsyncClient):
    response = await register_user(async_client=async_client,
                                   email="test@example.com",
                                   password="123456"
                                   )

    assert response.status_code == 201
    assert "User registered successfully" in response.json()["detail"]


@pytest.mark.anyio
async def test_register_user_already_exists(async_client: AsyncClient, registered_user: dict):
    response = await register_user(async_client=async_client,
                                   email=registered_user["email"],
                                   password=registered_user["password"]
                                   )

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
