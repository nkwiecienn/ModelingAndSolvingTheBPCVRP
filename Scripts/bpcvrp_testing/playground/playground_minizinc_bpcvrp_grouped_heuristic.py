from __future__ import annotations

from pathlib import Path

from bpcvrp_testing.generators.bpcsdvrp_generator import generate_random_bpcsdvrp
from bpcvrp_testing.io.io_utils import save_as_dzn
from bpcvrp_testing.solvers.bpcvrp_grouped_heuristic import solve_bpcvrp_grouped_heuristic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"


def test_1_generate_to_dzn():
    """
    Generates a BP instance with item lists (per customer) and saves to .dzn.
    This is useful if you want to inspect the instance or re-run from file.
    """
    inst = generate_random_bpcsdvrp(
        n_customers=10,
        area_size=80.0,
        instance_type="mixed",

        maxVisitsPerCustomer=3,   # unused in this heuristic, but generator needs it
        nbVehicles=4,
        vehicle_capacity=4,       # pallets per vehicle

        bin_capacity=40,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=3,
        max_items_per_customer=12,

        fraction_split_customers=0.35,
        seed=42,
    )
    inst.name = "bpcvrp_heuristic_seed42"

    out_dir = DATA_DIR / "bpcvrp_heuristic_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"

    save_as_dzn(inst, dzn_path)
    print("Saved instance to:", dzn_path)


def test_2_run_grouped_heuristic():
    """
    End-to-end run:
      - palletise each customer (BPP per customer)
      - count full vehicle trips (fixedCost)
      - solve reduced VRP on remainder groups
    """
    inst = generate_random_bpcsdvrp(
        n_customers=12,
        area_size=100.0,
        instance_type="clustered",

        nbVehicles=5,
        vehicle_capacity=4,       # pallets per vehicle
        maxVisitsPerCustomer=3,

        bin_capacity=40,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=3,
        max_items_per_customer=12,

        fraction_split_customers=0.40,
        seed=7,
    )
    inst.name = "bpcvrp_heuristic_demo"

    # You provide these models:
    bpp_model_path = MODELS_DIR / "bpp_002.mzn"
    vrp_grouped_model_path = MODELS_DIR / "vrp_004_grouped_orders.mzn"

    res = solve_bpcvrp_grouped_heuristic(
        instance_obj=inst,
        bpp_model_path=bpp_model_path,
        vrp_grouped_model_path=vrp_grouped_model_path,
        solver_name="chuffed",
        time_limit_per_customer=10.0,
        time_limit_vrp=300.0,
        fallback="volume_lb",
        nbVehicles=None,  # use N_remaining as upper bound (same style as vrp_002)
    )

    print("\n--- Palletisation summary ---")
    print("pallets_per_customer:", res.palletisation.pallets_per_customer)
    print("full_trips_per_customer:", res.palletisation.full_trips_per_customer)
    print("remainder_per_customer:", res.palletisation.remainder_per_customer)
    print("fixed_cost:", res.palletisation.fixed_cost)
    print("remaining_customer_ids:", res.palletisation.remaining_customer_ids)
    print("remaining_demands:", res.palletisation.remaining_demands)

    if res.grouped_instance is None:
        print("\nAll demand became fixed full-vehicle trips.")
        print("Total objective =", res.palletisation.fixed_cost)
        return

    print("\n--- Reduced VRP instance ---")
    print("N_remaining:", res.grouped_instance.N)
    print("nbVehicles:", res.grouped_instance.nbVehicles)
    print("Demand:", res.grouped_instance.Demand)
    print("fixedCost:", res.grouped_instance.fixedCost)

    print("\n--- VRP solve ---")
    print("status:", res.status)
    print("objective:", res.objective)
    if res.vrp_result and res.vrp_result.solution:
        print("solution keys:", list(res.vrp_result.solution.keys()))


if __name__ == "__main__":
    # test_1_generate_to_dzn()
    # test_2_run_grouped_heuristic()
    pass
