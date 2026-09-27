import pytest


@pytest.mark.asyncio
async def test_executors_seeded_and_crud(client):
    # 1. Verify preset seed data (21 executors)
    resp = await client.get("/api/v1/executors")
    assert resp.status_code == 200
    executors = resp.json()
    assert len(executors) >= 20

    # 2. Get specific executor
    resp = await client.get("/api/v1/executors/executor-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["executor_id"] == "executor-01"
    assert data["active"] is True
    assert data["capacity"] == 1.0

    # 3. Create new executor
    new_exec = {
        "executor_id": "executor-custom-99",
        "active": True,
        "capacity": 2.0,
        "daily_limit": 100,
        "attributes": {
            "order_types": ["LEGAL_REVIEW"],
            "regions": ["ural"],
        },
    }
    resp = await client.post("/api/v1/executors", json=new_exec)
    assert resp.status_code == 201
    assert resp.json()["version"] == 1

    # 4. Patch executor
    resp = await client.patch("/api/v1/executors/executor-custom-99", json={"capacity": 2.5, "active": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["capacity"] == 2.5
    assert data["active"] is False
    assert data["version"] == 2
