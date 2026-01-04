from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Optional

from bpcvrp_testing.io.io_utils import save_as_dzn
from bpcvrp_testing.io.experiment_utils import (
    is_optimal,
    save_result_json,
    print_solve_header,
    print_instance,
    print_solve_result,
    plot_runtime_vs_size,
)

from bpcvrp_testing.instances.bpp_instance import BPPInstance
from bpcvrp_testing.instances.vrp_instance import VRPInstance
from bpcvrp_testing.instances.sdvrp_instance import SDVRPInstance
from bpcvrp_testing.instances.bpcsdvrp_instance import BPCSDVRPInstance

from bpcvrp_testing.generators.bpp_generator import generate_random_bpp
from bpcvrp_testing.generators.vrp_generator import generate_random_vrp
from bpcvrp_testing.generators.sdvrp_generator import generate_random_sdvrp
from bpcvrp_testing.generators.bpcsdvrp_generator import generate_random_bpcsdvrp

from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

SOLVER_NAME = "cp-sat"
THREADS = 24

# Experiment controls
TIME_LIMIT = 2 * 60 * 60         # 2 hours
REPEATS_PER_N = 5                 # 5 different seeds per size
INSTANCE_TYPE = "uniform"
BASE_SEED = 42

# Integrated-instance controls (shared by BP-CVRP and BP-CVRP-SD)
BPCSD_MAX_VISITS = 3
BPCSD_VEHICLE_CAPACITY = 4        # capacity in pallets
BPCSD_BIN_CAPACITY = 50           # pallet capacity in item-size units
BPCSD_MIN_ITEM_RATIO = 0.2
BPCSD_MAX_ITEM_RATIO = 0.8
BPCSD_MIN_ITEMS_PER_CUST = 3
BPCSD_MAX_ITEMS_PER_CUST = 10
BPCSD_FRACTION_SPLIT_CUSTOMERS = 0.30
BPCSD_SPLIT_MIN_EXTRA_PALLETS = 1


def _seeds_for_n(n: int, base_seed: int = BASE_SEED, reps: int = REPEATS_PER_N) -> list[int]:
    """
    Deterministic, unique seeds per problem size n.
    Keeps your runs reproducible and avoids reusing the same seeds across sizes.
    """
    return [base_seed + 1000 * n + k for k in range(reps)]


def _timed_out(status: object, elapsed: float, time_limit: int) -> bool:
    """
    MiniZinc/solver statuses vary a bit; we use a conservative rule:
    - elapsed ~ time_limit  OR
    - status contains TIME / UNKNOWN
    """
    s = str(status).upper()
    if elapsed >= time_limit - 1.0:
        return True
    if "TIME" in s or "UNKNOWN" in s:
        return True
    return False


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate_for_plot(
    runs: list[dict[str, object]],
    x_key: str,
    *,
    group_key: Optional[str] = None,
) -> list[dict[str, object]]:
    """
    Convert many runs per n into one point per n:
      - time = mean(time)
      - optimal = True if ANY run was optimal (you can change to ALL if you prefer)
    """
    buckets: dict[tuple[object, object], list[dict[str, object]]] = {}
    for r in runs:
        x = r[x_key]
        g = r.get(group_key) if group_key else None
        buckets.setdefault((x, g), []).append(r)

    out: list[dict[str, object]] = []
    for (x, g), rs in sorted(buckets.items(), key=lambda t: (t[0][1] is not None, t[0][0], t[0][1])):
        times = [float(r["time"]) for r in rs if r.get("time") is not None]
        any_opt = any(bool(r.get("optimal")) for r in rs)
        row: dict[str, object] = {
            x_key: x,
            "time": _mean(times) if times else 0.0,
            "optimal": any_opt,
        }
        if group_key:
            row[group_key] = g
        out.append(row)
    return out


# -------------------------------------------------------------------
# BPP
# -------------------------------------------------------------------
def bpp():
    runs: list[dict[str, object]] = []
    stop = False

    for i in range(1, 11):
        n_items = 10 * i
        for seed in _seeds_for_n(n_items):
            inst: BPPInstance = generate_random_bpp(
                n=n_items,
                capacity=100,
                min_ratio=0.2,
                max_ratio=0.8,
                seed=seed,
            )

            model_path = MODELS_DIR / "bpp_002.mzn"
            data_path = DATA_DIR / "bpp" / f"bpp_n{n_items}_c100_seed{seed}.dzn"
            save_as_dzn(inst, data_path)

            runner = MiniZincRunner(model_path, solver_name=SOLVER_NAME)
            res = runner.solve_instance(inst, time_limit=TIME_LIMIT, threads=THREADS)

            result_path = RESULTS_DIR / "bpp" / f"bpp_n{n_items}_c100_seed{seed}.json"
            save_result_json(data_path, res, result_path)

            runs.append({
                "n": inst.n,
                "seed": seed,
                "time": res.time,
                "optimal": is_optimal(res.status),
                "status": str(res.status),
                "has_solution": getattr(res, "has_solution", None),
                "objective": getattr(res, "objective", None),
            })

            print_solve_header(f"BPP n={n_items}, seed={seed}")
            print_instance(inst)
            print("-" * 50)
            print_solve_result(res)

            if _timed_out(res.status, res.time, TIME_LIMIT):
                stop = True
                break

        if stop:
            break 

    plot_points = _aggregate_for_plot(runs, x_key="n")
    plot_runtime_vs_size(
        plot_points,
        x_key="n",
        title="BPP runtime vs n (mean over seeds)",
        xlabel="n (items)",
        out_path=RESULTS_DIR / "bpp" / "bpp_n_vs_time.png",
    )


# -------------------------------------------------------------------
# CVRP
# -------------------------------------------------------------------
def vrp():
    runs: list[dict[str, object]] = []
    stop = False

    for n in range(2, 10):
        for seed in _seeds_for_n(n):
            inst: VRPInstance = generate_random_vrp(
                n_customers=n,
                area_size=100.0,
                demand_min=1,
                demand_max=10,
                vehicle_capacity=None,
                vehicle_capacity_factor=1.1,
                target_vehicles=int(n / 3) + 1,
                instance_type=INSTANCE_TYPE,
                seed=seed,
            )

            model_path = MODELS_DIR / "vrp_002.mzn"
            data_path = DATA_DIR / "vrp" / f"vrp_{INSTANCE_TYPE}_n{n}_seed{seed}.dzn"
            save_as_dzn(inst, data_path)

            runner = MiniZincRunner(model_path, solver_name=SOLVER_NAME)
            res = runner.solve_instance(inst, time_limit=TIME_LIMIT, threads=THREADS)

            result_path = RESULTS_DIR / "vrp" / f"vrp_{INSTANCE_TYPE}_n{n}_seed{seed}.json"
            save_result_json(data_path, res, result_path)

            runs.append({
                "n_customers": inst.N,
                "seed": seed,
                "time": res.time,
                "optimal": is_optimal(res.status),
                "status": str(res.status),
                "has_solution": getattr(res, "has_solution", None),
                "objective": getattr(res, "objective", None),
                "instance_type": INSTANCE_TYPE,
            })

            print_solve_header(f"VRP n={n}, seed={seed} ({INSTANCE_TYPE})")
            print_instance(inst)
            print("-" * 50)
            print_solve_result(res)

            if _timed_out(res.status, res.time, TIME_LIMIT):
                stop = True
                break

        if stop:
            break

    plot_points = _aggregate_for_plot(runs, x_key="n_customers", group_key="instance_type")
    plot_runtime_vs_size(
        plot_points,
        x_key="n_customers",
        title="VRP runtime vs n_customers (mean over seeds)",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "vrp" / "vrp_n_customers_vs_time.png",
        group_key="instance_type",
    )


# -------------------------------------------------------------------
# SD-CVRP
# -------------------------------------------------------------------
def sdvrp():
    runs: list[dict[str, object]] = []

    for n in range(2, 10):
        for seed in _seeds_for_n(n):
            inst: SDVRPInstance = generate_random_sdvrp(
                n_customers=n,
                vehicle_capacity=20,
                demand_min=1,
                demand_max=10,
                maxVisitsPerCustomer=2,
                nbVehicles=None,
                fraction_oversized=0.30,
                ensure_feasible=True,
                area_size=100.0,
                instance_type=INSTANCE_TYPE,
                seed=seed,
            )

            model_path = MODELS_DIR / "vrp_003_split_delivery.mzn"
            data_path = DATA_DIR / "sdvrp" / f"sdvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.dzn"
            save_as_dzn(inst, data_path)

            runner = MiniZincRunner(model_path, solver_name=SOLVER_NAME)
            res = runner.solve_instance(inst, time_limit=TIME_LIMIT, threads=THREADS)

            result_path = RESULTS_DIR / "sdvrp" / f"sdvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.json"
            save_result_json(data_path, res, result_path)

            runs.append({
                "n_customers": inst.N,
                "seed": seed,
                "time": res.time,
                "optimal": is_optimal(res.status),
                "status": str(res.status),
                "has_solution": getattr(res, "has_solution", None),
                "objective": getattr(res, "objective", None),
                "instance_type": INSTANCE_TYPE,
            })

            print_solve_header(f"SDVRP n={n}, seed={seed} ({INSTANCE_TYPE})")
            print_instance(inst)
            print("-" * 50)
            print_solve_result(res)

            if _timed_out(res.status, res.time, TIME_LIMIT):
                stop = True
                break

        if stop:
            break

    plot_points = _aggregate_for_plot(runs, x_key="n_customers", group_key="instance_type")
    plot_runtime_vs_size(
        plot_points,
        x_key="n_customers",
        title="SDVRP runtime vs n_customers (mean over seeds)",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "sdvrp" / "sdvrp_n_customers_vs_time.png",
        group_key="instance_type",
    )


# -------------------------------------------------------------------
# Integrated: build ONE master BP-SD instance per (n, seed)
# and use it for both BP-CVRP and BP-CVRP-SD.
# -------------------------------------------------------------------
def _generate_master_bpcsdvrp(n: int, seed: int) -> BPCSDVRPInstance:
    max_items_cap = min(BPCSD_MAX_ITEMS_PER_CUST, BPCSD_MAX_VISITS * BPCSD_VEHICLE_CAPACITY)

    inst: BPCSDVRPInstance = generate_random_bpcsdvrp(
        n_customers=n,
        area_size=100.0,
        instance_type=INSTANCE_TYPE,
        seed=seed,

        maxVisitsPerCustomer=BPCSD_MAX_VISITS,
        nbVehicles=None,
        vehicle_capacity=BPCSD_VEHICLE_CAPACITY,
        vehicle_capacity_factor=1.0,

        bin_capacity=BPCSD_BIN_CAPACITY,
        min_item_ratio=BPCSD_MIN_ITEM_RATIO,
        max_item_ratio=BPCSD_MAX_ITEM_RATIO,
        min_items_per_customer=BPCSD_MIN_ITEMS_PER_CUST,
        max_items_per_customer=max_items_cap,

        fraction_split_customers=BPCSD_FRACTION_SPLIT_CUSTOMERS,
        split_min_extra_pallets=BPCSD_SPLIT_MIN_EXTRA_PALLETS,
    )

    # Ensure global feasibility even under worst-case "1 item = 1 pallet"
    worst_case_total_pallets = sum(inst.ItemsPerCustomer)
    min_vehicles = max(1, int(ceil(worst_case_total_pallets / inst.Capacity)))
    if inst.nbVehicles < min_vehicles:
        inst.nbVehicles = min_vehicles

    return inst


def bpcsdvrp():
    """
    BP-CVRP with Split Deliveries (integrated model).
    """
    runs: list[dict[str, object]] = []

    for n in range(2, 10):
        for seed in _seeds_for_n(n):
            inst = _generate_master_bpcsdvrp(n, seed)

            model_path = MODELS_DIR / "bpcvrp_002_split_deliveries.mzn"
            data_path = DATA_DIR / "bpcsdvrp" / f"bpcsdvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.dzn"
            save_as_dzn(inst, data_path)

            runner = MiniZincRunner(model_path, solver_name=SOLVER_NAME)
            res = runner.solve_instance(inst, time_limit=TIME_LIMIT, threads=THREADS)

            result_path = RESULTS_DIR / "bpcsdvrp" / f"bpcsdvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.json"
            save_result_json(data_path, res, result_path)

            runs.append({
                "n_customers": inst.N,
                "seed": seed,
                "time": res.time,
                "optimal": is_optimal(res.status),
                "status": str(res.status),
                "has_solution": getattr(res, "has_solution", None),
                "objective": getattr(res, "objective", None),
                "instance_type": INSTANCE_TYPE,
                "nbVehicles": inst.nbVehicles,
            })

            print_solve_header(f"BPCSDVRP n={n}, seed={seed} ({INSTANCE_TYPE})")
            print_instance(inst)
            print("-" * 50)
            print_solve_result(res)

            if _timed_out(res.status, res.time, TIME_LIMIT):
                stop = True
                break

        if stop:
            break

    # Plot mean runtime vs n (over seeds)
    plot_points = _aggregate_for_plot(runs, x_key="n_customers", group_key="instance_type")
    plot_runtime_vs_size(
        plot_points,
        x_key="n_customers",
        title="BPCSDVRP runtime vs n_customers (mean over seeds)",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "bpcsdvrp" / "bpcsdvrp_n_customers_vs_time.png",
        group_key="instance_type",
    )


def bpcvrp():
    """
    BP-CVRP baseline integrated model (single visit per customer).
    Uses the SAME master instances as bpcsdvrp() for fair comparison.
    Some instances may be UNSAT (and that's OK to record).
    """
    runs: list[dict[str, object]] = []

    for n in range(2, 10):
        for seed in _seeds_for_n(n):
            master = _generate_master_bpcsdvrp(n, seed)
            inst = master.to_bpcvrp()  # <-- same Distance + same item lists

            model_path = MODELS_DIR / "bpcvrp_001.mzn"
            data_path = DATA_DIR / "bpcvrp" / f"bpcvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.dzn"
            save_as_dzn(inst, data_path)

            runner = MiniZincRunner(model_path, solver_name=SOLVER_NAME)
            res = runner.solve_instance(inst, time_limit=TIME_LIMIT, threads=THREADS)

            result_path = RESULTS_DIR / "bpcvrp" / f"bpcvrp_{INSTANCE_TYPE}_n{n}_seed{seed}.json"
            save_result_json(data_path, res, result_path)

            runs.append({
                "n_customers": inst.N,
                "seed": seed,
                "time": res.time,
                "optimal": is_optimal(res.status),
                "status": str(res.status),
                "has_solution": getattr(res, "has_solution", None),
                "objective": getattr(res, "objective", None),
                "instance_type": INSTANCE_TYPE,
            })

            print_solve_header(f"BPCVRP n={n}, seed={seed} ({INSTANCE_TYPE})")
            print_instance(inst)
            print("-" * 50)
            print_solve_result(res)

            if _timed_out(res.status, res.time, TIME_LIMIT):
                stop = True
                break

        if stop:
            break

    plot_points = _aggregate_for_plot(runs, x_key="n_customers", group_key="instance_type")
    plot_runtime_vs_size(
        plot_points,
        x_key="n_customers",
        title="BPCVRP runtime vs n_customers (mean over seeds)",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "bpcvrp" / "bpcvrp_n_customers_vs_time.png",
        group_key="instance_type",
    )


if __name__ == "__main__":
    # bpp()
    vrp()
    # sdvrp()
    # bpcvrp()
    # bpcsdvrp()
    pass
