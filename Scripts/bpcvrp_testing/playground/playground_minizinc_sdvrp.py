from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from bpcvrp_testing.io.io_utils import save_as_dzn
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner
from bpcvrp_testing.experiments.batch_runner import run_batch, save_results_csv
from bpcvrp_testing.generators.sdvrp_generator import generate_random_sdvrp

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Scripts/
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"


def _fallback_compute_sdvrp_metrics(instance: Any, sol: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal SD metrics that work even if you don't have sdvrp_metrics.py yet.
    Assumes the model outputs:
      - delivered: array[NODES] of ...
    Uses instance fields:
      - N, maxVisitsPerCustomer, Demand (if available)
    """
    if not sol or "delivered" not in sol:
        return {}

    delivered = sol["delivered"]

    # In the SD model we used: customer copies are 1..(N*maxVisitsPerCustomer)
    N = getattr(instance, "N", None)
    mv = getattr(instance, "maxVisitsPerCustomer", None)
    if not isinstance(N, int) or not isinstance(mv, int) or N <= 0 or mv <= 0:
        return {}

    nb_copies = N * mv
    delivered_copies = delivered[:nb_copies]  # first block is customer copies

    # visits per customer: count copies with delivered > 0
    visits = [0] * N
    for idx, val in enumerate(delivered_copies, start=1):
        if val and val > 0:
            c = 1 + ((idx - 1) // mv)  # origCustomer mapping
            visits[c - 1] += 1

    n_split_customers = sum(1 for v in visits if v >= 2)
    n_active_copies = sum(1 for v in delivered_copies if v and v > 0)
    max_visits = max(visits) if visits else 0
    avg_visits = (sum(visits) / N) if N else 0.0

    return {
        "n_active_copies": n_active_copies,
        "n_split_customers": n_split_customers,
        "max_visits_per_customer_used": max_visits,
        "avg_visits_per_customer_used": round(avg_visits, 4),
    }


try:
    from bpcvrp_testing.experiments.sdvrp_metrics import compute_sdvrp_metrics  # type: ignore
except Exception:
    compute_sdvrp_metrics = None


def _sd_metrics(inst: Any, res: Any) -> Dict[str, Any]:
    if not res.solution:
        return {}
    if compute_sdvrp_metrics is not None:
        return compute_sdvrp_metrics(inst, res.solution)
    return _fallback_compute_sdvrp_metrics(inst, res.solution)


def test_1_sdvrp_generate_to_dzn():
    """
    Generates a single SDVRP instance (with some demands exceeding Capacity)
    and saves it to a .dzn file.
    """
    inst = generate_random_sdvrp(
        n_customers=4,
        area_size=100.0,
        vehicle_capacity=40,
        demand_min=5,
        demand_max=120,
        maxVisitsPerCustomer=3,
        fraction_oversized=0.30,
        seed=123,
    )
    inst.name = "sdvrp_n4_seed123"

    out_dir = DATA_DIR / "sdvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"

    print(f"Generated SDVRP: N={inst.N}, Capacity={inst.Capacity}, "
          f"maxVisitsPerCustomer={inst.maxVisitsPerCustomer}, nbVehicles={inst.nbVehicles}")

    save_as_dzn(inst, dzn_path)
    print("Saved .dzn to:", dzn_path)


def test_2_sdvrp_generate_and_solve():
    """
    Generates a single SDVRP instance and solves it via MiniZincRunner.
    Prints a few SD-specific metrics to quickly confirm splitting happens when needed.
    """
    inst = generate_random_sdvrp(
        n_customers=4,
        area_size=80.0,
        vehicle_capacity=35,
        demand_min=5,
        demand_max=110,
        maxVisitsPerCustomer=3,
        fraction_oversized=0.35,
        seed=42,
    )
    inst.name = "sdvrp_n4_seed42"

    model_path = MODELS_DIR / "vrp_003_split_delivery.mzn"
    runner = MiniZincRunner(model_path, solver_name="cp-sat")

    res = runner.solve_instance(inst, time_limit=120, threads=12)

    print("SDVRP solve status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)

    if res.solution:
        print("Solution keys:", list(res.solution.keys()))
        print("SD metrics:", _sd_metrics(inst, res))


def test_3_sdvrp_batch():
    """
    Generates several SDVRP instances with different seeds and runs them via batch runner.
    Adds SD-specific metrics to the CSV output via extra_metrics_fn.
    """
    instances = []
    for s in range(5):
        inst = generate_random_sdvrp(
            n_customers=5,
            area_size=100.0,
            vehicle_capacity=50,
            demand_min=5,
            demand_max=160,
            maxVisitsPerCustomer=3,
            fraction_oversized=0.25,
            seed=s,
        )
        inst.name = f"sdvrp_n5_seed{s}"
        instances.append(inst)

    model_path = MODELS_DIR / "vrp_003_split_delivery.mzn"
    rows = run_batch(
        instances,
        model_path=model_path,
        solver_name="cp-sat",
        time_limit=300.0,
        threads=24,
        print_progress=True,
        extra_metrics_fn=lambda inst, res: _sd_metrics(inst, res),
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / "sdvrp_batch_24threads.csv"
    save_results_csv(rows, csv_path)
    print("Saved SDVRP batch results to:", csv_path)


def test_4_sdvrp_tiny_debug():
    """
    Very small SDVRP instance for manual inspection in IDE / model debugging.
    Intentionally includes oversized demands so split deliveries are exercised.
    """
    inst = generate_random_sdvrp(
        n_customers=5,
        area_size=50.0,
        vehicle_capacity=20,
        demand_min=5,
        demand_max=70,
        maxVisitsPerCustomer=3,
        fraction_oversized=0.50,
        seed=7,
    )
    inst.name = "sdvrp_tiny_debug"

    out_dir = DATA_DIR / "sdvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"
    save_as_dzn(inst, dzn_path)
    print("Tiny SDVRP saved to:", dzn_path)

    model_path = MODELS_DIR / "vrp_003_split_delivery.mzn"
    runner = MiniZincRunner(model_path, solver_name="chuffed")
    res = runner.solve_instance(inst, time_limit=120)

    print("Tiny SDVRP status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)
    if res.solution:
        print("SD metrics:", _sd_metrics(inst, res))


if __name__ == "__main__":
    # test_1_sdvrp_generate_to_dzn()
    # test_2_sdvrp_generate_and_solve()
    test_3_sdvrp_batch()
    # test_4_sdvrp_tiny_debug()
    pass
