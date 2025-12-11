from bpcvrp_testing.generators.bpp_generator import generate_random_bpp
from bpcvrp_testing.generators.vrp_generator import generate_random_vrp
from bpcvrp_testing.solvers.ortools_bpp_runner import ORToolsBPPRunner
from bpcvrp_testing.solvers.ortools_vrp_runner import ORToolsVRPRunner

def test_ortools_bpp_generate_and_solve():
    inst = generate_random_bpp(
        n=30,
        capacity=100,
        min_ratio=0.2,
        max_ratio=0.8,
        seed=42,
    )

    runner = ORToolsBPPRunner(solver_name="SCIP")
    res = runner.solve_instance(inst, time_limit=60)

    print("ORTools BPP solve status:", res.status)
    print("Objective (bins used):", res.objective)
    print("Time [s]:", res.time)
    if res.solution:
        print("Bins used:", len(res.solution["bin_items"]))
        for b, items in res.solution["bin_items"].items():
            print(f"  Bin {b}: items {items}")

def test_ortools_vrp_generate_and_solve():
    inst = generate_random_vrp(
        n_customers=8,
        area_size=100.0,
        demand_min=1,
        demand_max=5,
        vehicle_capacity=None,
        vehicle_capacity_factor=1.0,
        target_vehicles=3,
        instance_type="uniform",
        seed=1,
    )

    print(str(inst))

    runner = ORToolsVRPRunner()
    res = runner.solve_instance(inst, time_limit=60)

    print("ORTools VRP solve status:", res.status)
    print("Objective (total distance):", res.objective)
    print("Time [s]:", res.time)
    if res.solution:
        print("Routes:")
        for i, route in enumerate(res.solution["routes"]):
            print(f"  Vehicle {i}: {route}")

if __name__ == "__main__":
    # test_ortools_bpp_generate_and_solve()
    # test_ortools_vrp_generate_and_solve()
    pass
