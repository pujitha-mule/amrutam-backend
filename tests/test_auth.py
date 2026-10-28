
import uuid

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"new-{uuid.uuid4().hex}@example.com",
            "password": "correct horse battery staple",
            "full_name": "New Patient",
            "phone": "9876543210",
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
