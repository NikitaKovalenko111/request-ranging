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
    assert status_data["executors"]["total"] >= 200
    assert status_data["executors"]["active"] >= 198

    # 3. Test instant 1000 orders burst ("в один момент приходило 1к заявок")
    resp_1k = await client.post("/api/v1/simulation/burst", json={"count": 1000})
    assert resp_1k.status_code == 200
    assert resp_1k.json()["details"]["burst_orders"] == 1000

    # Verify orders increased by 1000
    resp_after = await client.get("/api/v1/simulation/status")
    assert resp_after.status_code == 200
    assert resp_after.json()["orders"]["total"] >= 1100


@pytest.mark.asyncio
async def test_lifecycle_simulator_execution(client):
    import asyncio
    from simulation.app.generator.lifecycle import lifecycle_simulator
    from simulation.app.storage.database import async_session_factory
    from simulation.app.storage.repository import OrderRepository

    # Seed an order to allow lifecycle transitions and verify update_order 5-tuple unpack
    async with async_session_factory() as session:
        order_repo = OrderRepository(session)
        await order_repo.create(
            order_id="order-lifecycle-test-1",
            parent_id=None,
            status="processed",
            weight=1.0,
            attributes={"sum": 100000, "order_type": "LEGAL_REVIEW", "subject": "contract"},
            version=1,
        )
        updated_row, _, status_changed, prev_status, _ = await order_repo.update_order(
            order_id="order-lifecycle-test-1",
            new_status="accept",
        )
        assert updated_row is not None
        assert status_changed is True
        assert prev_status == "processed"
        assert updated_row.status == "accept"
        assert updated_row.version == 2

    # Start and stop lifecycle simulator to verify it initializes and runs cleanly
    await lifecycle_simulator.start()
    assert lifecycle_simulator.is_running() is True
    await asyncio.sleep(0.1)
    await lifecycle_simulator.stop()
    assert lifecycle_simulator.is_running() is False


@pytest.mark.asyncio
async def test_lifecycle_only_selects_assigned_orders(client):
    from simulation.app.storage.database import async_session_factory
    from simulation.app.storage.repository import OrderRepository

    async with async_session_factory() as session:
        repo = OrderRepository(session)
        # 1. Unassigned order (just created by generator)
        await repo.create(
            order_id="order-unassigned",
            parent_id=None,
            status="processed",
            weight=1.0,
            attributes={"sum": 100000, "order_type": "LEGAL_REVIEW", "subject": "contract"},
            version=1,
        )
        # 2. Assigned order (assigned by balancer)
        await repo.create(
            order_id="order-assigned",
            parent_id=None,
            status="processed",
            weight=1.0,
            attributes={"sum": 200000, "order_type": "LEGAL_REVIEW", "subject": "contract"},
            version=1,
        )
        await repo.assign_executor("order-assigned", "executor-01")

        # 3. Verify get_random_orders with assigned_only=True returns ONLY order-assigned
        assigned_candidates = await repo.get_random_orders(status="processed", assigned_only=True, limit=50)
        candidate_ids = [c.order_id for c in assigned_candidates]
        assert "order-assigned" in candidate_ids
        assert "order-unassigned" not in candidate_ids


