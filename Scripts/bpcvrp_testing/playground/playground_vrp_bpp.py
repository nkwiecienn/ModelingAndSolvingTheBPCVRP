from __future__ import annotations

from pathlib import Path

from bpcvrp_testing.io.io_utils import load_txt_bpp, load_txt_vrp, save_as_dzn
from bpcvrp_testing.instances.bpp_instance import BPPInstance
from bpcvrp_testing.instances.vrp_instance import VRPInstance
from bpcvrp_testing.generators.bpp_generator import generate_random_bpp
from bpcvrp_testing.generators.vrp_generator import generate_random_vrp
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner
from bpcvrp_testing.experiments.batch_runner import run_batch, save_results_csv


BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Scripts/
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"


def test_1_bpp_txt_to_dzn():
    txt_path = DATA_DIR / "bpp_txt" / "BPP_50_50_0.1_0.7_0.txt"
    dzn_path = DATA_DIR / "bpp_dzn" / (txt_path.stem + ".dzn")

    inst = load_txt_bpp(txt_path)
    print("BPP from txt:", inst)

    save_as_dzn(inst, dzn_path)
    print("Zapisano .dzn do:", dzn_path)


def test_2_vrp_txt_to_dzn():
    vrp_path = DATA_DIR / "vrp_txt" / "P-n16-k8.vrp.txt"
    dzn_path = DATA_DIR / "vrp_dzn" / (vrp_path.stem + ".dzn")

    inst = load_txt_vrp(vrp_path)
    print("VRP from txt: N, Capacity =", inst.N, inst.Capacity)

    save_as_dzn(inst, dzn_path)
    print("Zapisano .dzn do:", dzn_path)


def test_3_bpp_generate_to_dzn():
    inst: BPPInstance = generate_random_bpp(
        n=20,
        capacity=100,
        min_ratio=0.2,
        max_ratio=0.8,
        seed=123,
    )
    dzn_path = DATA_DIR / "bpp_dzn" / "gen_bpp_20_100.dzn"
    print("Generated BPP:", inst.n, inst.capacity, inst.sizes[:5], "...")
    save_as_dzn(inst, dzn_path)
    print("Zapisano .dzn do:", dzn_path)


def test_4_vrp_generate_to_dzn():
    inst: VRPInstance = generate_random_vrp(
        n_customers=20,
        area_size=100.0,
        demand_min=1,
        demand_max=10,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=4,
        instance_type="clustered",
        seed=42,
    )
    dzn_path = DATA_DIR / "vrp_dzn" / "gen_vrp_n20.dzn"
    print("Generated VRP:", inst.N, inst.Capacity)
    save_as_dzn(inst, dzn_path)
    print("Zapisano .dzn do:", dzn_path)


def test_5_bpp_generate_and_solve():
    inst: BPPInstance = generate_random_bpp(
        n=30,
        capacity=100,
        min_ratio=0.2,
        max_ratio=0.8,
        seed=7,
    )

    model_path = MODELS_DIR / "bpp_002.mzn"
    runner = MiniZincRunner(model_path, solver_name="chuffed")

    res = runner.solve_instance(inst, time_limit=60)
    print("BPP solve status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)
    if res.solution:
        print("Solution keys:", list(res.solution.keys()))


def test_6_vrp_generate_and_solve():
    inst: VRPInstance = generate_random_vrp(
        n_customers=15,
        area_size=100.0,
        demand_min=1,
        demand_max=10,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=3,
        instance_type="uniform",
        seed=99,
    )

    model_path = MODELS_DIR / "vrp_002.mzn"
    runner = MiniZincRunner(model_path, solver_name="chuffed")

    res = runner.solve_instance(inst, time_limit=120)
    print("VRP solve status:", res.status)
    print("Objective:", res.objective)
    print("Time [s]:", res.time)
    if res.solution:
        print("Solution keys:", list(res.solution.keys()))


def test_7_bpp_batch():
    instances = []
    for i in range(5):
        inst = generate_random_bpp(
            n=40,
            capacity=100,
            min_ratio=0.2,
            max_ratio=0.8,
            seed=i,
        )
        inst.name = f"bpp_n40_seed{i}"
        instances.append(inst)

    model_path = MODELS_DIR / "bpp_002.mzn"
    rows = run_batch(
        instances,
        model_path=model_path,
        solver_name="chuffed",
        time_limit=60.0,
        print_progress=True,
    )

    csv_path = RESULTS_DIR / "bpp_batch_example.csv"
    save_results_csv(rows, csv_path)
    print("Zapisano wyniki batch BPP do:", csv_path)


def test_8_vrp_batch():
    instances = []
    for i in range(5):
        inst = generate_random_vrp(
            n_customers=25,
            area_size=100.0,
            demand_min=1,
            demand_max=10,
            vehicle_capacity=None,
            vehicle_capacity_factor=1.0,
            target_vehicles=4,
            instance_type="mixed",
            seed=i,
        )
        inst.name = f"vrp_n25_seed{i}"
        instances.append(inst)

    model_path = MODELS_DIR / "vrp_002.mzn"
    rows = run_batch(
        instances,
        model_path=model_path,
        solver_name="chuffed",
        time_limit=120.0,
        print_progress=True,
    )

    csv_path = RESULTS_DIR / "vrp_batch_example.csv"
    save_results_csv(rows, csv_path)
    print("Zapisano wyniki batch VRP do:", csv_path)


if __name__ == "__main__":
    test_1_bpp_txt_to_dzn()
    # test_2_vrp_txt_to_dzn()
    # test_3_bpp_generate_to_dzn()
    # test_4_vrp_generate_to_dzn()
    # test_5_bpp_generate_and_solve()
    # test_6_vrp_generate_and_solve()
    # test_7_bpp_batch()
    # test_8_vrp_batch()
    pass
