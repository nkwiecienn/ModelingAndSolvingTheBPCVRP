from __future__ import annotations

from pathlib import Path

from bpcvrp_testing.generators.bpcvrp_generator import generate_random_bpcvrp
from bpcvrp_testing.io.io_utils import save_as_dzn
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner
from bpcvrp_testing.experiments.batch_runner import run_batch, save_results_csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"


def test_1_bpcvrp_generate_to_dzn():
    """
    Generates a single BPCVRP instance and saves it to a .dzn file.
    """
    inst = generate_random_bpcvrp(
        n_customers=4,
        area_size=100.0,
        instance_type="clustered",
        # VRP
        demand_min=1,
        demand_max=5,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=2,
        # BPP per customer
        bin_capacity=10,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=2,
        max_items_per_customer=5,
        seed=123,
    )

    inst.name = "bpcvrp_n4_clustered_seed123"

    out_dir = DATA_DIR / "bpcvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"

    print(f"Generated BPCVRP: N={inst.N}, Capacity={inst.Capacity}, "
          f"binCapacity={inst.binCapacity}")
    print(f"ItemsPerCustomer: {inst.ItemsPerCustomer}")

    save_as_dzn(inst, dzn_path)
    print("Saved .dzn to:", dzn_path)


def test_2_bpcvrp_generate_and_solve():
    """
    Generates a single BPCVRP instance and solves it via MiniZincRunner.
    """
    inst = generate_random_bpcvrp(
        n_customers=8,
        area_size=80.0,
        instance_type="uniform",
        demand_min=1,
        demand_max=5,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=2,
        bin_capacity=40,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=2,
        max_items_per_customer=5,
        seed=42,
    )
    inst.name = "bpcvrp_n8_uniform_seed42"

    model_path = MODELS_DIR / "bpcvrp_001.mzn"
    runner = MiniZincRunner(model_path, solver_name="chuffed")

    res = runner.solve_instance(inst, time_limit=300)

    print("BPCVRP solve status:", res.status)
    print("Objective (travel time / distance):", res.objective)
    print("Time [s]:", res.time)

    if res.solution:
        print("Solution vars:", list(res.solution.keys()))


def test_3_bpcvrp_batch():
    """
    Generates several BPCVRP instances with different seeds and runs them via batch runner.
    Results are saved to CSV.
    """
    instances = []
    for s in range(5):
        inst = generate_random_bpcvrp(
            n_customers=12,
            area_size=100.0,
            instance_type="mixed",
            demand_min=1,
            demand_max=6,
            vehicle_capacity=None,
            vehicle_capacity_factor=1.0,
            target_vehicles=3,
            bin_capacity=50,
            min_item_ratio=0.2,
            max_item_ratio=0.8,
            min_items_per_customer=3,
            max_items_per_customer=8,
            seed=s,
        )
        inst.name = f"bpcvrp_n12_mixed_seed{s}"
        instances.append(inst)

    model_path = MODELS_DIR / "bpcvrp_001.mzn"
    rows = run_batch(
        instances,
        model_path=model_path,
        solver_name="chuffed",
        time_limit=600.0,
        print_progress=True,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / "bpcvrp_batch_example.csv"
    save_results_csv(rows, csv_path)
    print("Saved BPCVRP batch results to:", csv_path)


def test_4_bpcvrp_tiny_debug():
    """
    Very small BPCVRP instance for manual inspection in IDE / model debugging.
    """
    inst = generate_random_bpcvrp(
        n_customers=4,
        area_size=50.0,
        instance_type="clustered",
        demand_min=1,
        demand_max=3,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=2,
        bin_capacity=20,
        min_item_ratio=0.2,
        max_item_ratio=0.8,
        min_items_per_customer=2,
        max_items_per_customer=4,
        seed=7,
    )
    inst.name = "bpcvrp_tiny_debug"

    out_dir = DATA_DIR / "bpcvrp_dzn"
    out_dir.mkdir(parents=True, exist_ok=True)
    dzn_path = out_dir / f"{inst.name}.dzn"
    save_as_dzn(inst, dzn_path)
    print("Tiny BPCVRP saved to:", dzn_path)

    model_path = MODELS_DIR / "bpcvrp_001.mzn"
    runner = MiniZincRunner(model_path, solver_name="chuffed")
    res = runner.solve_instance(inst, time_limit=120)

    print("Tiny BPCVRP status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)


if __name__ == "__main__":
    # test_1_bpcvrp_generate_to_dzn()
    # test_2_bpcvrp_generate_and_solve()
    # test_3_bpcvrp_batch()
    # test_4_bpcvrp_tiny_debug()
    pass
