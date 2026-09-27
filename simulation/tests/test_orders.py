import pytest


@pytest.mark.asyncio
async def test_order_crud_and_versioning(client):
    # 1. Create Order
    create_payload = {
        "order_id": "order-test-1",
        "parent_id": None,
        "status": "processed",
        "weight": 2.0,
        "attributes": {
            "sum": 900000,
            "order_type": "LEGAL_REVIEW",
            "subject": "contract",
            "vip": True,
            "region": "ural",
        },
    }
    resp = await client.post("/api/v1/orders", json=create_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_id"] == "order-test-1"
    assert data["status"] == "processed"
    assert data["version"] == 1
    assert data["weight"] == 2.0
    assert data["attributes"]["vip"] is True

    # 2. Get Order
    resp = await client.get("/api/v1/orders/order-test-1")
    assert resp.status_code == 200
    assert resp.json()["order_id"] == "order-test-1"

    # 3. Patch Order Attributes (version increment)
    patch_payload = {
        "weight": 2.5,
        "attributes": {"region": "siberia"},
    }
    resp = await client.patch("/api/v1/orders/order-test-1", json=patch_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 2
    assert data["weight"] == 2.5
    assert data["attributes"]["region"] == "siberia"
    assert data["attributes"]["sum"] == 900000  # Preserved

    # 4. Patch Order Status
    resp = await client.patch("/api/v1/orders/order-test-1", json={"status": "accept"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 3
    assert data["status"] == "accept"

    # 5. List Orders
    resp = await client.get("/api/v1/orders")
    assert resp.status_code == 200
    orders = resp.json()
    assert len(orders) >= 1
