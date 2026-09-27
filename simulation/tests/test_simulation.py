import pytest


@pytest.mark.asyncio
async def test_simulation_burst_and_status(client):
    # 1. Trigger burst of 100 orders
    resp = await client.post("/api/v1/simulation/burst", json={"count": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "burst_completed"
    assert data["details"]["burst_orders"] == 100

    # 2. Check simulation status
    resp = await client.get("/api/v1/simulation/status")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["orders"]["total"] >= 100
    assert status_data["executors"]["total"] >= 20
    assert status_data["executors"]["active"] >= 15

    # 3. Test instant 1000 orders burst ("в один момент приходило 1к заявок")
    resp_1k = await client.post("/api/v1/simulation/burst", json={"count": 1000})
    assert resp_1k.status_code == 200
    assert resp_1k.json()["details"]["burst_orders"] == 1000

    # Verify orders increased by 1000
    resp_after = await client.get("/api/v1/simulation/status")
    assert resp_after.status_code == 200
    assert resp_after.json()["orders"]["total"] >= 1100
