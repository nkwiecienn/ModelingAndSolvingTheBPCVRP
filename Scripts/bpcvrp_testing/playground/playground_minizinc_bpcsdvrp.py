from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from bpcvrp_testing.generators.bpcsdvrp_generator import generate_random_bpcsdvrp
from bpcvrp_testing.io.io_utils import save_as_dzn
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner
from bpcvrp_testing.experiments.batch_runner import run_batch, save_results_csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"


def _sd_metrics_from_solution(N: int, maxVisitsPerCustomer: int, sol: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a small SD summary from MiniZinc solution dict.

    Assumptions (same as your SDVRP model):
      - customer copies are indexed 1..N*maxVisitsPerCustomer
      - delivered is defined for all nodes; depots have delivered = 0
    """
    if not sol:
        return {}

    delivered = sol.get("delivered")
    demand = sol.get("Demand")  # derived pallets per customer in the combined model

    if not isinstance(delivered, list):
        return {}

    nb_copies = N * maxVisitsPerCustomer
    delivered_copies: List[int] = [int(x) for x in delivered[:nb_copies]]

    visits = [0] * N
    delivered_sum = [0] * N

    for idx, val in enumerate(delivered_copies, start=1):
        if val > 0:
            c = 1 + ((idx - 1) // maxVisitsPerCustomer)  # origCustomer
            visits[c - 1] += 1
            delivered_sum[c - 1] += val

    n_split_customers = sum(1 for v in visits if v >= 2)
    n_active_copies = sum(1 for v in delivered_copies if v > 0)

    out: Dict[str, Any] = {
        "n_active_copies": n_active_copies,
        "n_split_customers": n_split_customers,
        "max_visits_used": max(visits) if visits else 0,
        "avg_visits_used": round(sum(visits) / N, 4) if N else 0.0,
    }

    # Optional: validate demand satisfaction if Demand is present
    if isinstance(demand, list) and len(demand) == N:
        demand_int = [int(x) for x in demand]
        out["demand_satisfied"] = all(delivered_sum[i] == demand_int[i] for i in range(N))
        out["max_pallet_demand"] = max(demand_int) if demand_int else 0
        out["avg_pallet_demand"] = round(sum(demand_int) / N, 4) if N else 0.0

    return out


def test_1_bpcsdvrp_generate_to_dzn():
    """
    Generates a single BP-SDVRP instance and saves it to a .dzn file.
    """
    inst = generate_random_bpcsdvrp(
        n_customers=4,
        area_size=100.0,
        instance_type="clustered",

        # SD
        maxVisitsPerCustomer=3,
        nbVehicles=3,
        vehicle_capacity=4,                 # pallets per vehicle

        # BPP per customer
        bin_capacity=40,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=3,
        max_items_per_customer=10,

        # force some customers to require split deliveries
        fraction_split_customers=0.35,
        seed=123,
    )
    inst.name = "bpcsdvrp_n4_seed123"

    out_dir = DATA_DIR / "bpcsdvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"

    print(f"Generated BP-SDVRP: N={inst.N}, nbVehicles={inst.nbVehicles}, "
          f"Capacity(pallets)={inst.Capacity}, maxVisits={inst.maxVisitsPerCustomer}, "
          f"binCapacity={inst.binCapacity}")
    print(f"ItemsPerCustomer: {inst.ItemsPerCustomer}")

    save_as_dzn(inst, dzn_path)
    print("Saved .dzn to:", dzn_path)


def test_2_bpcsdvrp_generate_and_solve():
    """
    Generates a single BP-SDVRP instance and solves it via MiniZincRunner.
    """
    inst = generate_random_bpcsdvrp(
        n_customers=4,
        area_size=40.0,
        instance_type="uniform",

        maxVisitsPerCustomer=3,
        nbVehicles=12,
        vehicle_capacity=4,

        bin_capacity=10,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=5,
        max_items_per_customer=10,

        fraction_split_customers=0.30,
        seed=42,
    )
    inst.name = "bpcsdvrp_n4_notimelimit"

    model_path = MODELS_DIR / "bpcvrp_002_split_deliveries.mzn"
    runner = MiniZincRunner(model_path, solver_name="cp-sat")

    res = runner.solve_instance(inst, threads=24)

    print("BP-SDVRP solve status:", res.status)
    print("Objective (travel time / distance):", res.objective)
    print("Time [s]:", res.time)

    if res.solution:
        print("Solution vars:", list(res.solution.keys()))
        print("SD metrics:", _sd_metrics_from_solution(inst.N, inst.maxVisitsPerCustomer, res.solution))


def test_3_bpcsdvrp_batch():
    """
    Generates several BP-SDVRP instances and runs them via batch runner.
    Adds split-delivery metrics into the CSV output.
    """
    instances = []
    for s in range(3):
        inst = generate_random_bpcsdvrp(
            n_customers=4,
            area_size=100.0,
            instance_type="mixed",

            maxVisitsPerCustomer=3,
            nbVehicles=5,
            vehicle_capacity=5,

            bin_capacity=10,
            min_item_ratio=0.2,
            max_item_ratio=0.8,
            min_items_per_customer=1,
            max_items_per_customer=5,

            fraction_split_customers=0.25,
            seed=s,
        )
        inst.name = f"bpcsdvrp_n5_seed{s}"
        instances.append(inst)

    model_path = MODELS_DIR / "bpcvrp_002_split_deliveries.mzn"
    rows = run_batch(
        instances,
        model_path=model_path,
        solver_name="cp-sat",
        time_limit=3600.0,
        threads=24,
        print_progress=True,
        extra_metrics_fn=lambda inst, res: _sd_metrics_from_solution(
            inst.N, inst.maxVisitsPerCustomer, res.solution or {}
        ),
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / "bpcsdvrp_batch_example.csv"
    save_results_csv(rows, csv_path)
    print("Saved BP-SDVRP batch results to:", csv_path)


def test_4_bpcsdvrp_tiny_debug():
    """
    Very small BP-SDVRP instance for manual inspection / model debugging.
    """
    inst = generate_random_bpcsdvrp(
        n_customers=5,
        area_size=50.0,
        instance_type="clustered",

        maxVisitsPerCustomer=3,
        nbVehicles=3,
        vehicle_capacity=3,

        bin_capacity=30,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=1,
        max_items_per_customer=5,

        fraction_split_customers=0.40,
        seed=7,
    )
    inst.name = "bpcsdvrp_tiny_debug"

    out_dir = DATA_DIR / "bpcsdvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"
    save_as_dzn(inst, dzn_path)
    print("Tiny BP-SDVRP saved to:", dzn_path)

    model_path = MODELS_DIR / "bpcvrp_002_split_deliveries.mzn"
    runner = MiniZincRunner(model_path, solver_name="cp-sat")
    res = runner.solve_instance(inst, time_limit=120, threads=24)

    print("Tiny BP-SDVRP status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)

    if res.solution:
        print("SD metrics:", _sd_metrics_from_solution(inst.N, inst.maxVisitsPerCustomer, res.solution))


if __name__ == "__main__":
    # test_1_bpcsdvrp_generate_to_dzn()
    test_2_bpcsdvrp_generate_and_solve()
    # test_3_bpcsdvrp_batch()
    # test_4_bpcsdvrp_tiny_debug()
    pass
