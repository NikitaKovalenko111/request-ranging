import argparse
import asyncio
import os
import sys

# Ensure repository root and simulation are in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.app.storage.database import init_db, async_session_factory
from simulation.app.generator.seeds import seed_database
from simulation.app.generator.load import load_generator
from simulation.app.storage.repository import OrderRepository, ExecutorRepository, AssignmentRepository


async def main():
    parser = argparse.ArgumentParser(description="AIS Simulator CLI Load Generator")
    parser.add_argument("--seed", action="store_true", help="Seed 21 preset executors")
    parser.add_argument("--burst", type=int, default=0, help="Trigger instant burst of N orders (e.g. --burst 1000)")
    parser.add_argument("--mode", type=str, default="linear_with_spikes", choices=["linear_with_spikes", "stream_4k", "wave", "normal", "slow", "burst_at_start"], help="Generation pattern (default: linear_with_spikes = ~4000/hour with spikes)")
    parser.add_argument("--rate-hour", type=float, default=4000.0, help="Target orders per hour (default: 4000)")
    parser.add_argument("--max-peak", type=int, default=5, help="Max orders per second during spikes (default: 5)")
    parser.add_argument("--status", action="store_true", help="Print current database metrics")
    args = parser.parse_args()

    await init_db()

    async with async_session_factory() as session:
        if args.seed:
            print("Seeding database with preset executors...")
            await seed_database(session)
            print("Seeding complete.")

    if args.burst > 0:
        print(f"Executing instant burst of {args.burst} orders...")
        res = await load_generator.execute_burst(count=args.burst)
        print(f"Burst complete: {res}")

    if args.target > 0:
        print(f"Starting load generator towards {args.target} orders (mode='{args.mode}', rate={args.rate_hour}/h, max_peak={args.max_peak}/s)...")
        await load_generator.start(
            mode=args.mode,
            target=args.target,
            orders_per_hour=args.rate_hour,
            max_peak_per_sec=args.max_peak,
        )
        try:
            while load_generator.is_running():
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    count = await repo.count_orders()
                print(f"[Generator] Orders in DB: {count}/{args.target} | Current rate: {load_generator.current_rate} req/s", end="\r")
                if count >= args.target:
                    print(f"\nTarget {args.target} orders reached!")
                    break
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("\nStopping generator...")
        finally:
            await load_generator.stop()

    if args.status or (not args.seed and args.burst == 0 and args.target == 0):
        async with async_session_factory() as session:
            o_repo = OrderRepository(session)
            e_repo = ExecutorRepository(session)
            a_repo = AssignmentRepository(session)

            total_orders = await o_repo.count_orders()
            proc_orders = await o_repo.count_orders(status="processed")
            await_orders = await o_repo.count_orders(status="await")
            accept_orders = await o_repo.count_orders(status="accept")
            reject_orders = await o_repo.count_orders(status="reject")

            total_executors = await e_repo.count_executors()
            active_executors = await e_repo.count_executors(active=True)
            total_assignments = await a_repo.count_assignments()

            print("\n=== AIS Simulator Database Metrics ===")
            print(f"Executors:   {total_executors} total ({active_executors} active)")
            print(f"Orders:      {total_orders} total")
            print(f"  Processed: {proc_orders}")
            print(f"  Await:     {await_orders}")
            print(f"  Accept:    {accept_orders}")
            print(f"  Reject:    {reject_orders}")
            print(f"Assignments: {total_assignments} confirmed")
            print("======================================\n")


if __name__ == "__main__":
    asyncio.run(main())
