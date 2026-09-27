import pytest


@pytest.mark.asyncio
async def test_assignments_contract(client):
    # 1. Prepare Order
    order_payload = {
        "order_id": "order-assign-test",
        "parent_id": None,
        "status": "processed",
        "weight": 1.5,
        "attributes": {
            "sum": 500000,
            "order_type": "LEGAL_REVIEW",
            "subject": "contract",
            "vip": True,
        },
    }
    resp = await client.post("/api/v1/orders", json=order_payload)
    assert resp.status_code == 201

    # 2. Normal Assignment to active executor-01
    assign_payload = {
        "assignment_id": "assign-uuid-1",
        "order_id": "order-assign-test",
        "executor_id": "executor-01",
        "decided_at": "2026-09-25T12:00:01Z",
    }
    resp = await client.post(
        "/api/v1/assignments",
        json=assign_payload,
        headers={"Idempotency-Key": "assign-uuid-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignment_id"] == "assign-uuid-1"
    assert data["order_id"] == "order-assign-test"
    assert data["executor_id"] == "executor-01"
    assert data["status"] == "confirmed"
    assert "confirmed_at" in data

    # 3. Idempotency: repeating identical request returns same result
    resp_repeat = await client.post(
        "/api/v1/assignments",
        json=assign_payload,
        headers={"Idempotency-Key": "assign-uuid-1"},
    )
    assert resp_repeat.status_code == 200
    assert resp_repeat.json() == data

    # 4. Conflict (409): order already assigned, trying to assign to another executor
    conflict_payload = {
        "assignment_id": "assign-uuid-conflict",
        "order_id": "order-assign-test",
        "executor_id": "executor-02",
        "decided_at": "2026-09-25T12:00:05Z",
    }
    resp_conflict = await client.post("/api/v1/assignments", json=conflict_payload)
    assert resp_conflict.status_code == 409
    err = resp_conflict.json()
    assert err["code"] == "ORDER_ALREADY_ASSIGNED"

    # 5. Visibility: GET /api/v1/orders/order-assign-test shows assigned executor
    resp_order = await client.get("/api/v1/orders/order-assign-test")
    assert resp_order.status_code == 200
    assert resp_order.json()["assigned_executor_id"] == "executor-01"

    # 6. Unprocessable (422): Inactive executor (executor-19 is inactive in seed)
    order_payload_2 = {
        "order_id": "order-inactive-test",
        "status": "processed",
        "weight": 1.0,
        "attributes": {"sum": 100000, "order_type": "LEGAL_REVIEW", "subject": "contract", "vip": False},
    }
    await client.post("/api/v1/orders", json=order_payload_2)

    resp_inactive = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-uuid-inactive",
            "order_id": "order-inactive-test",
            "executor_id": "executor-19",  # inactive
            "decided_at": "2026-09-25T12:00:01Z",
        },
    )
    assert resp_inactive.status_code == 422
    assert resp_inactive.json()["code"] == "EXECUTOR_INACTIVE"

    # 7. Unprocessable (422): Order not in 'processed' status
    await client.patch("/api/v1/orders/order-inactive-test", json={"status": "accept"})
    resp_status_error = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-uuid-bad-status",
            "order_id": "order-inactive-test",
            "executor_id": "executor-01",
            "decided_at": "2026-09-25T12:00:01Z",
        },
    )
    assert resp_status_error.status_code == 422
    assert resp_status_error.json()["code"] == "INVALID_ORDER_STATUS"

    # 8. Not Found (404)
    resp_not_found = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-uuid-nf",
            "order_id": "order-non-existent",
            "executor_id": "executor-01",
            "decided_at": "2026-09-25T12:00:01Z",
        },
    )
    assert resp_not_found.status_code == 404
    assert resp_not_found.json()["code"] == "ORDER_NOT_FOUND"
