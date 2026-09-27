import pytest
from simulation.app.kafka.producer import kafka_producer


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

    # 6. Simultaneous Patch (both parameters and status change) -> Sequential versions (v and v+1)
    resp_create = await client.post("/api/v1/orders", json={
        "order_id": "order-simultaneous-patch",
        "status": "processed",
        "weight": 1.0,
        "attributes": {
            "sum": 100000,
            "order_type": "LEGAL_REVIEW",
            "subject": "contract",
            "vip": False,
        },
    })
    assert resp_create.status_code == 201
    kafka_producer.in_memory_log.clear()

    patch_both_resp = await client.patch(
        "/api/v1/orders/order-simultaneous-patch",
        json={"weight": 3.0, "status": "accept"},
    )
    assert patch_both_resp.status_code == 200
    patched_data = patch_both_resp.json()
    assert patched_data["weight"] == 3.0
    assert patched_data["status"] == "accept"
    assert patched_data["version"] == 3

    # Check published events: OrderUpdated (v=2) then OrderStatusChanged (v=3)
    events = [entry["event"] for entry in kafka_producer.in_memory_log]
    types = [e["event_type"] for e in events]
    assert types == ["OrderUpdated", "OrderStatusChanged"]
    assert events[0]["payload"]["version"] == 2
    assert events[1]["payload"]["version"] == 3
    assert events[1]["payload"]["previous_status"] == "processed"
    assert events[1]["payload"]["status"] == "accept"


@pytest.mark.asyncio
async def test_kafka_error_propagation(client):
    from simulation.app.config import settings
    old_kafka_enabled = settings.kafka_enabled
    settings.kafka_enabled = True
    try:
        resp = await client.post("/api/v1/orders", json={
            "order_id": "order-kafka-fail",
            "status": "processed",
            "weight": 1.0,
            "attributes": {
                "sum": 100000,
                "order_type": "LEGAL_REVIEW",
                "subject": "contract",
                "vip": False,
            },
        })
        assert resp.status_code == 500
        data = resp.json()
        assert data["code"] == "KAFKA_PUBLISH_FAILED"
        assert data["retryable"] is True
    finally:
        settings.kafka_enabled = old_kafka_enabled
