from __future__ import annotations
import json
from pathlib import Path

from bpcvrp_testing.generators.bpcvrp_generator import generate_random_bpcvrp
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
from bpcvrp_testing.generators.bpp_generator import generate_random_bpp
from bpcvrp_testing.generators.vrp_generator import generate_random_vrp
from bpcvrp_testing.generators.bpcsdvrp_generator import generate_random_bpcsdvrp
from bpcvrp_testing.generators.sdvrp_generator import generate_random_sdvrp
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner
from bpcvrp_testing.solvers.bpcvrp_grouped_heuristic import solve_bpcvrp_grouped_heuristic


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

def bpp():
    results: list[dict[str, object]] = []
    for i in range(1, 11):
        inst: BPPInstance = generate_random_bpp(
            n=10*i,
            capacity=100,
            min_ratio=0.2,
            max_ratio=0.8,
            seed=42,
        )

        model_path = MODELS_DIR / "bpp_002.mzn"
        data_path = DATA_DIR / f"bpp/bpp_n{i}0_c100_seed42.dzn"
        save_as_dzn(inst, data_path)

        runner = MiniZincRunner(model_path, solver_name="cp-sat")
        res = runner.solve_instance(inst, time_limit=180, threads=24)

        result_path = RESULTS_DIR / "bpp" / f"bpp_n{i}0_c100_seed42.json"
        save_result_json(data_path, res, result_path)

        results.append({
            "n": inst.n,
            "time": res.time,
            "optimal": is_optimal(res.status),
        })

        print_solve_header(f"BPP run {i}")
        print_instance(inst)
        print("-" * 50)
        print_solve_result(res)

    plot_runtime_vs_size(
        results,
        x_key="n",
        title="BPP runtime vs n",
        xlabel="n (items)",
        out_path=RESULTS_DIR / "bpp" / "bpp_n_vs_time.png",
    )

def vrp():
    results: list[dict[str, object]] = []
    instance_type = "uniform"
    for i in range(2, 10):
        inst: VRPInstance = generate_random_vrp(
            n_customers=i,
            area_size=100.0,
            demand_min=1,
            demand_max=10,
            vehicle_capacity=None,
            vehicle_capacity_factor=1.1,
            target_vehicles=int(i/3)+1,
            instance_type=instance_type,
            seed=42,
        )

        model_path = MODELS_DIR / "vrp_002.mzn"
        data_path = DATA_DIR / f"vrp/vrp_{instance_type}_n{i}_seed42.dzn"
        save_as_dzn(inst, data_path)

        runner = MiniZincRunner(model_path, solver_name="cp-sat")
        res = runner.solve_instance(inst, time_limit=720, threads=24)

        result_path = RESULTS_DIR / "vrp" / f"vrp_{instance_type}_n{i}_seed42.json"
        save_result_json(data_path, res, result_path)

        results.append({
            "n_customers": inst.N,
            "time": res.time,
            "optimal": is_optimal(res.status),
        })

        print_solve_header(f"VRP run {i} ({instance_type})")
        print_instance(inst)
        print("-" * 50)
        print_solve_result(res)

    plot_runtime_vs_size(
        results,
        x_key="n_customers",
        title="VRP runtime vs n_customers",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "vrp" / "vrp_n_customers_vs_time.png",
    )

def bpcvrp():
    results: list[dict[str, object]] = []

    instance_type = "uniform"
    for i in range(2, 10):
        inst = generate_random_bpcvrp(
            # ----- VRP part -----
            n_customers=i,
            area_size=100.0,
            demand_min=1,
            demand_max=10,
            vehicle_capacity=None,
            vehicle_capacity_factor=1.1,
            target_vehicles=int(i/3) + 1,
            instance_type=instance_type,
            seed=42,

            # ----- BPP part (per customer) -----
            bin_capacity=50,
            min_item_ratio=0.2,
            max_item_ratio=0.8,
            min_items_per_customer=3,
            max_items_per_customer=10,
        )

        model_path = MODELS_DIR / "bpcvrp_001.mzn"
        data_path = DATA_DIR / f"bpcvrp/bpcvrp_{instance_type}_n{i}_seed42.dzn"
        save_as_dzn(inst, data_path)

        runner = MiniZincRunner(model_path, solver_name="cp-sat")
        res = runner.solve_instance(inst, time_limit=720, threads=24)

        result_path = RESULTS_DIR / "bpcvrp" / f"bpcvrp_{instance_type}_n{i}_seed42.json"
        save_result_json(data_path, res, result_path)

        results.append({
            "n_customers": inst.N,
            "time": res.time,
            "optimal": is_optimal(res.status),
            "instance_type": instance_type,
        })

        print_solve_header(f"BPCVRP run {i} ({instance_type})")
        print_instance(inst)
        print("-" * 50)
        print_solve_result(res)

    plot_runtime_vs_size(
        results,
        x_key="n_customers",
        title="BPCVRP runtime vs n_customers",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "bpcvrp" / "bpcvrp_n_customers_vs_time.png",
        group_key="instance_type",
    )

def sdvrp():
    results: list[dict[str, object]] = []

    instance_type = "uniform"
    for i in range(2, 10):
        inst: SDVRPInstance = generate_random_sdvrp(
            n_customers=i,

            # SD-specific controls
            vehicle_capacity=20,          # capacity per vehicle (in demand units)
            demand_min=1,
            demand_max=10,
            maxVisitsPerCustomer=2,
            nbVehicles=None,              # let generator choose minimum feasible nbVehicles
            fraction_oversized=0.30,      # ensure split deliveries appear
            ensure_feasible=True,
            area_size=100.0,
            instance_type=instance_type,
            seed=42,
        )

        model_path = MODELS_DIR / "vrp_003_split_delivery.mzn"
        data_path = DATA_DIR / f"sdvrp/sdvrp_{instance_type}_n{i}_seed42.dzn"
        save_as_dzn(inst, data_path)

        runner = MiniZincRunner(model_path, solver_name="cp-sat")
        res = runner.solve_instance(inst, time_limit=720, threads=24)

        result_path = RESULTS_DIR / "sdvrp" / f"sdvrp_{instance_type}_n{i}_seed42.json"
        save_result_json(data_path, res, result_path)

        results.append({
            "n_customers": inst.N,
            "time": res.time,
            "optimal": is_optimal(res.status),
        })

        print_solve_header(f"SDVRP run {i} ({instance_type})")
        print_instance(inst)
        print("-" * 50)
        print_solve_result(res)

    plot_runtime_vs_size(
        results,
        x_key="n_customers",
        title="SDVRP runtime vs n_customers",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "sdvrp" / "sdvrp_n_customers_vs_time.png",
    )

def bpcvrp_grouped():
    results: list[dict[str, object]] = []

    instance_type = "uniform"
    for i in range(2, 10):
        inst = generate_random_bpcsdvrp(
            n_customers=i,
            area_size=100.0,
            instance_type=instance_type,
            seed=42,

            vehicle_capacity=4,
            nbVehicles=int(i / 3) + 1,

            bin_capacity=50,
            min_item_ratio=0.2,
            max_item_ratio=0.8,
            min_items_per_customer=3,
            max_items_per_customer=10,

            fraction_split_customers=0.30,
            maxVisitsPerCustomer=3,
        )

        model_tag = f"{instance_type}_n{i}_seed42"
        data_path = DATA_DIR / f"bpcvrp_grouped/bpcsdvrp_{model_tag}.dzn"
        save_as_dzn(inst, data_path)

        bpp_model_path = MODELS_DIR / "bpp_002.mzn"
        vrp_grouped_model_path = MODELS_DIR / "vrp_004_grouped_orders.mzn"

        res = solve_bpcvrp_grouped_heuristic(
            instance_obj=inst,
            bpp_model_path=bpp_model_path,
            vrp_grouped_model_path=vrp_grouped_model_path,
            solver_name="cp-sat",
            time_limit_per_customer=10.0,
            time_limit_vrp=720.0,
            fallback="volume_lb",
            nbVehicles=None,
        )

        result_path = RESULTS_DIR / "bpcvrp_grouped" / f"bpcvrp_grouped_{model_tag}.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "instance_path": str(data_path),
            "status": res.status,
            "objective": res.objective,
            "fixed_cost": res.palletisation.fixed_cost,
            "pallets_per_customer": res.palletisation.pallets_per_customer,
            "full_trips_per_customer": res.palletisation.full_trips_per_customer,
            "remainder_per_customer": res.palletisation.remainder_per_customer,
            "remaining_customer_ids": res.palletisation.remaining_customer_ids,
            "remaining_demands": res.palletisation.remaining_demands,
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        vrp_time = 0.0
        if res.vrp_result is not None and res.vrp_result.time is not None:
            vrp_time = float(res.vrp_result.time)

        results.append({
            "n_customers": inst.N,
            "time": vrp_time,
            "optimal": is_optimal(res.status),
            "instance_type": instance_type,
        })

        print_solve_header(f"BPCVRP grouped heuristic run {i} ({instance_type})")
        print_instance(inst)
        print("-" * 50)
        print(f"Status     : {res.status}")
        print(f"Objective  : {res.objective}")
        print(f"fixedCost  : {res.palletisation.fixed_cost}")
        print(f"VRP time[s]: {vrp_time:.2f}")

    plot_runtime_vs_size(
        results,
        x_key="n_customers",
        group_key="instance_type",
        title="BPCVRP grouped heuristic runtime vs n_customers",
        xlabel="n_customers",
        out_path=RESULTS_DIR / "bpcvrp_grouped" / "plots",
    )


if __name__ == "__main__":
    # bpp()
    # vrp()
    # bpcvrp()
    sdvrp()
    pass
