import asyncio
import pytest
from simulation.app.config import settings


@pytest.mark.asyncio
async def test_assignments_contract(client):
    # 0. Test Idempotency-Key header validation
    resp_no_header = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-no-header",
            "order_id": "order-assign-test",
            "executor_id": "executor-01",
            "decided_at": "2026-09-25T12:00:01Z",
        },
    )
    assert resp_no_header.status_code == 400
    assert resp_no_header.json()["code"] == "INVALID_IDEMPOTENCY_KEY"

    resp_mismatch_header = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-mismatch",
            "order_id": "order-assign-test",
            "executor_id": "executor-01",
            "decided_at": "2026-09-25T12:00:01Z",
        },
        headers={"Idempotency-Key": "different-key"},
    )
    assert resp_mismatch_header.status_code == 400
    assert resp_mismatch_header.json()["code"] == "INVALID_IDEMPOTENCY_KEY"

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
    resp_conflict = await client.post(
        "/api/v1/assignments",
        json=conflict_payload,
        headers={"Idempotency-Key": "assign-uuid-conflict"},
    )
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
    resp_o2 = await client.post("/api/v1/orders", json=order_payload_2)
    assert resp_o2.status_code == 201

    resp_inactive = await client.post(
        "/api/v1/assignments",
        json={
            "assignment_id": "assign-uuid-inactive",
            "order_id": "order-inactive-test",
            "executor_id": "executor-19",  # inactive
            "decided_at": "2026-09-25T12:00:01Z",
        },
        headers={"Idempotency-Key": "assign-uuid-inactive"},
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
        headers={"Idempotency-Key": "assign-uuid-bad-status"},
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
        headers={"Idempotency-Key": "assign-uuid-nf"},
    )
    assert resp_not_found.status_code == 404
    assert resp_not_found.json()["code"] == "ORDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_concurrent_assignments(client):
    """
    Test concurrency protection:
    1. Parallel requests with different assignment_ids to the same order -> exactly one 200, others 409.
    2. Parallel duplicate requests with identical assignment_id to the same order -> both 200 without primary key collision.
    """
    # Create order for test 1
    resp_ord1 = await client.post("/api/v1/orders", json={
        "order_id": "order-concurrency-1",
        "status": "processed",
        "weight": 1.0,
        "attributes": {
            "sum": 100000,
            "order_type": "LEGAL_REVIEW",
            "subject": "contract",
            "vip": False,
        },
    })
    assert resp_ord1.status_code == 201

    # Simulate realistic delay for concurrency test
    old_min, old_max = settings.assignment_delay_min, settings.assignment_delay_max
    settings.assignment_delay_min = 0.05
    settings.assignment_delay_max = 0.10

    try:
        # 1. Two concurrent requests to same order with different assignment_ids
        task1 = client.post(
            "/api/v1/assignments",
            json={
                "assignment_id": "assign-c1-a",
                "order_id": "order-concurrency-1",
                "executor_id": "executor-01",
                "decided_at": "2026-09-25T12:00:01Z",
            },
            headers={"Idempotency-Key": "assign-c1-a"},
        )
        task2 = client.post(
            "/api/v1/assignments",
            json={
                "assignment_id": "assign-c1-b",
                "order_id": "order-concurrency-1",
                "executor_id": "executor-02",
                "decided_at": "2026-09-25T12:00:01Z",
            },
            headers={"Idempotency-Key": "assign-c1-b"},
        )

        res1, res2 = await asyncio.gather(task1, task2)
        statuses = {res1.status_code, res2.status_code}
        assert statuses == {200, 409}, f"Expected {200, 409}, got {statuses}"

        # 2. Parallel duplicate requests with identical assignment_id
        resp_ord2 = await client.post("/api/v1/orders", json={
            "order_id": "order-concurrency-2",
            "status": "processed",
            "weight": 1.0,
            "attributes": {
                "sum": 200000,
                "order_type": "LEGAL_REVIEW",
                "subject": "contract",
                "vip": False,
            },
        })
        assert resp_ord2.status_code == 201

        dup_payload = {
            "assignment_id": "assign-dup-1",
            "order_id": "order-concurrency-2",
            "executor_id": "executor-03",
            "decided_at": "2026-09-25T12:00:01Z",
        }
        dup_headers = {"Idempotency-Key": "assign-dup-1"}

        task_dup1 = client.post("/api/v1/assignments", json=dup_payload, headers=dup_headers)
        task_dup2 = client.post("/api/v1/assignments", json=dup_payload, headers=dup_headers)

        res_dup1, res_dup2 = await asyncio.gather(task_dup1, task_dup2)
        assert res_dup1.status_code == 200
        assert res_dup2.status_code == 200
        assert res_dup1.json()["assignment_id"] == "assign-dup-1"
        assert res_dup2.json()["assignment_id"] == "assign-dup-1"

    finally:
        settings.assignment_delay_min = old_min
        settings.assignment_delay_max = old_max
