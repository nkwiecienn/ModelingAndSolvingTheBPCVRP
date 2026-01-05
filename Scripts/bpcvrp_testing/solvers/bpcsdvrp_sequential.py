from __future__ import annotations

from dataclasses import dataclass, asdict
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from bpcvrp_testing.instances.bpcsdvrp_instance import BPCSDVRPInstance
from bpcvrp_testing.instances.bpp_instance import BPPInstance
from bpcvrp_testing.instances.vrp_instance import VRPInstance
from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner, SolveResult


PathLike = Union[str, Path]


@dataclass
class CustomerPacking:
    customer: int                      # 1..N (original customer id)
    item_sizes: List[int]              # raw item sizes (length ItemsPerCustomer[customer])
    pallets: int                       # pallets used (nBins)
    bpp_status: str                    # status returned by MiniZinc
    bpp_time: float                    # solve time (seconds)
    bin_of_item: Optional[List[int]]   # list length len(item_sizes), value in 1..pallets
    pallets_items: Optional[List[List[int]]]  # pallet -> list of item indices (1-based)


@dataclass
class GroupingResult:
    """
    Output of the grouping step.

    - full_trips[c] = number of full vehicle trips (each of size Q) assigned to customer c
    - remaining_demand[c] = pallets that remain to be routed for customer c (0..Q-1 or Q if keep_equal_capacity)
    """
    fixed_cost: int
    full_trips: Dict[int, int]
    full_trip_routes: List[Dict[str, Any]]  # explicit depot->customer->depot trips
    remaining_customers: List[int]
    remaining_demands: List[int]
    orig_customer_of_node: List[int]   # index k (1..len(remaining_customers)) -> original customer id


@dataclass
class GroupedHeuristicSolution:
    """
    End-to-end result of the sequential pallet-grouping heuristic.
    Stored as a plain dict under SolveResult.solution.
    """
    packing: List[Dict[str, Any]]
    grouping: Dict[str, Any]
    vrp_instance: Optional[Dict[str, Any]]
    vrp_result: Optional[Dict[str, Any]]
    objective_breakdown: Dict[str, Any]


# -----------------------------
# Helpers: BPP per customer
# -----------------------------

def _extract_nbins(res: SolveResult) -> Optional[int]:
    """
    Try to read the number of bins/pallets from the BPP solve result.
    Accepts:
      - res.solution['nBins']  (your models)
      - res.objective          (if objective is nBins)
    """
    if res.solution and "nBins" in res.solution and res.solution["nBins"] is not None:
        try:
            return int(res.solution["nBins"])
        except Exception:
            pass
    if res.objective is not None:
        try:
            return int(res.objective)
        except Exception:
            pass
    return None


def _reconstruct_pallets(bin_of_item: List[int], pallets: int) -> List[List[int]]:
    """
    Convert bin assignment into explicit pallets:
      - bin_of_item[i] in 1..pallets
      - return list of pallets, each is list of item indices (1-based)
    """
    groups: List[List[int]] = [[] for _ in range(pallets)]
    for item_idx_0, b in enumerate(bin_of_item):
        if 1 <= b <= pallets:
            groups[b - 1].append(item_idx_0 + 1)
    return groups


def solve_bpp_for_customer(
    *,
    customer: int,
    item_sizes: List[int],
    bin_capacity: int,
    bpp_model_path: PathLike,
    solver_name: str = "cp-sat",
    time_limit: Optional[float] = None,
    threads: Optional[int] = None,
    fallback: str = "items_ub",
) -> CustomerPacking:
    """
    Solve per-customer BPP and return how many pallets are needed.

    Fallbacks (used when MiniZinc returns no solution):
      - "items_ub": pallets = number of items (always feasible upper bound)
      - "volume_lb": pallets = ceil(sum / bin_capacity) (lower bound; may be infeasible as a packing)
    """
    if len(item_sizes) == 0:
        return CustomerPacking(
            customer=customer,
            item_sizes=[],
            pallets=0,
            bpp_status="SKIPPED_EMPTY",
            bpp_time=0.0,
            bin_of_item=[],
            pallets_items=[],
        )

    bpp_inst = BPPInstance(n=len(item_sizes), capacity=int(bin_capacity), sizes=[int(x) for x in item_sizes])

    runner = MiniZincRunner(Path(bpp_model_path), solver_name=solver_name)
    res = runner.solve_instance(bpp_inst, time_limit=time_limit, threads=threads)

    nbins = _extract_nbins(res)

    if nbins is None:
        if fallback == "volume_lb":
            nbins = int(ceil(sum(item_sizes) / float(bin_capacity)))
        else:
            nbins = len(item_sizes)  # safe upper bound (one item per pallet)

        return CustomerPacking(
            customer=customer,
            item_sizes=item_sizes,
            pallets=nbins,
            bpp_status=f"{res.status} (fallback={fallback})",
            bpp_time=float(res.time),
            bin_of_item=None,
            pallets_items=None,
        )

    bin_of_item: Optional[List[int]] = None
    pallets_items: Optional[List[List[int]]] = None

    if res.solution and "b" in res.solution and res.solution["b"] is not None:
        try:
            # In MiniZinc, b is usually 1-based bin index per item
            raw = res.solution["b"]
            bin_of_item = [int(v) for v in raw]
            pallets_items = _reconstruct_pallets(bin_of_item, nbins)
        except Exception:
            bin_of_item = None
            pallets_items = None

    return CustomerPacking(
        customer=customer,
        item_sizes=item_sizes,
        pallets=nbins,
        bpp_status=res.status,
        bpp_time=float(res.time),
        bin_of_item=bin_of_item,
        pallets_items=pallets_items,
    )


# -----------------------------
# Stage 2: grouping pallets
# -----------------------------

def group_pallet_demands(
    *,
    pallet_counts: Sequence[int],
    distance: Sequence[Sequence[int]],
    vehicle_capacity: int,
    treat_equal_capacity_as_fixed: bool = False,
) -> GroupingResult:
    """
    Apply the grouping rule:

      - If p_c <= Q: keep as a single routed demand (p_c),
        unless treat_equal_capacity_as_fixed=True and p_c == Q.

      - If p_c > Q: remove full trips (each of size Q) as fixed depot->c->depot routes.
        Keep the remainder r = p_c % Q (if r > 0) for routing.

    Returns fixed_cost (sum of direct-trip costs) and the remaining customer list + demands.
    """
    Q = int(vehicle_capacity)
    fixed_cost = 0
    full_trips: Dict[int, int] = {}
    full_trip_routes: List[Dict[str, Any]] = []

    remaining_customers: List[int] = []
    remaining_demands: List[int] = []
    orig_customer_of_node: List[int] = []

    # pallet_counts indexed by customer-1 (customers are 1..N)
    for c_idx_0, p in enumerate(pallet_counts):
        c = c_idx_0 + 1

        if p <= Q and not (treat_equal_capacity_as_fixed and p == Q):
            if p > 0:
                remaining_customers.append(c)
                remaining_demands.append(int(p))
                orig_customer_of_node.append(c)
            continue

        # p > Q, or p == Q and we treat it as fixed
        if p == 0:
            continue

        trips = p // Q if Q > 0 else 0
        rem = p % Q if Q > 0 else p

        # If p == Q and treat_equal_capacity_as_fixed: trips = 1, rem = 0
        if treat_equal_capacity_as_fixed and p == Q:
            trips = 1
            rem = 0

        if trips > 0:
            # distance matrix uses index 0 = depot, 1..N = customers
            trip_cost = int(distance[0][c]) + int(distance[c][0])
            fixed_cost += trips * trip_cost
            full_trips[c] = trips
            full_trip_routes.append({
                "customer": c,
                "trips": trips,
                "pallets_per_trip": Q,
                "trip_cost": trip_cost,
                "total_cost": trips * trip_cost,
                "route": [0, c, 0],
            })

        if rem > 0:
            remaining_customers.append(c)
            remaining_demands.append(int(rem))
            orig_customer_of_node.append(c)

    return GroupingResult(
        fixed_cost=int(fixed_cost),
        full_trips=full_trips,
        full_trip_routes=full_trip_routes,
        remaining_customers=remaining_customers,
        remaining_demands=remaining_demands,
        orig_customer_of_node=orig_customer_of_node,
    )


def build_reduced_vrp_instance(
    *,
    original_distance: Sequence[Sequence[int]],
    remaining_customers: Sequence[int],
    remaining_demands: Sequence[int],
    vehicle_capacity: int,
) -> VRPInstance:
    """
    Build a classical VRP instance for the reduced problem.

    Conventions:
      - VRPInstance.Distance is (N+1)x(N+1) with index 0 = depot.
      - remaining_customers are original customer ids (1..N_original).
      - The reduced instance uses a new numbering: 1..N_rem.
    """
    nodes = [0] + [int(c) for c in remaining_customers]  # original ids, depot first
    N_rem = len(remaining_customers)

    dist: List[List[int]] = []
    for i in nodes:
        row = [int(original_distance[i][j]) for j in nodes]
        dist.append(row)

    return VRPInstance(
        N=N_rem,
        Capacity=int(vehicle_capacity),
        Demand=[int(d) for d in remaining_demands],
        Distance=dist,
    )


# -----------------------------
# Full heuristic pipeline
# -----------------------------

def solve_bpcsdvrp_grouped_heuristic(
    *,
    inst: BPCSDVRPInstance,
    bpp_model_path: PathLike,
    vrp_model_path: PathLike,
    solver_name: str = "cp-sat",
    threads: Optional[int] = 24,
    time_limit_bpp_per_customer: Optional[float] = None,
    time_limit_vrp: Optional[float] = None,
    treat_equal_capacity_as_fixed: bool = False,
    fallback_bpp: str = "items_ub",
) -> SolveResult:
    """
    Sequential pallet-grouping heuristic:

      (1) Run BPP per customer to get pallet counts p_c.
      (2) Group pallet counts using capacity Q:
            - full trips become fixed depot->customer->depot cost
            - remainder (and all p_c <= Q) becomes a classical CVRP instance
      (3) Solve the reduced CVRP (no split deliveries).
      (4) Return total objective = fixed_cost + routing_objective.

    Total runtime is measured from the start of the first BPP solve until the end of the VRP solve.
    The returned SolveResult.solution includes packing + grouping + VRP output.
    """
    t0 = perf_counter()

    # Stage 1: palletise each customer
    packing_rows: List[CustomerPacking] = []
    pallet_counts: List[int] = []

    for c in range(1, inst.N + 1):
        k = int(inst.ItemsPerCustomer[c - 1])
        sizes_row = [int(x) for x in inst.SizesOfItems[c - 1][:k] if int(x) > 0]

        pack = solve_bpp_for_customer(
            customer=c,
            item_sizes=sizes_row,
            bin_capacity=int(inst.binCapacity),
            bpp_model_path=bpp_model_path,
            solver_name=solver_name,
            time_limit=time_limit_bpp_per_customer,
            threads=threads,
            fallback=fallback_bpp,
        )
        packing_rows.append(pack)
        pallet_counts.append(int(pack.pallets))

    # Stage 2: group pallets + compute fixed cost
    grouping = group_pallet_demands(
        pallet_counts=pallet_counts,
        distance=inst.Distance,
        vehicle_capacity=int(inst.Capacity),
        treat_equal_capacity_as_fixed=treat_equal_capacity_as_fixed,
    )

    fixed_cost = int(grouping.fixed_cost)

    # Stage 3: reduced VRP
    vrp_inst: Optional[VRPInstance] = None
    vrp_res: Optional[SolveResult] = None
    routing_objective: float = 0.0

    if len(grouping.remaining_customers) > 0:
        vrp_inst = build_reduced_vrp_instance(
            original_distance=inst.Distance,
            remaining_customers=grouping.remaining_customers,
            remaining_demands=grouping.remaining_demands,
            vehicle_capacity=int(inst.Capacity),
        )
        vrp_runner = MiniZincRunner(Path(vrp_model_path), solver_name=solver_name)
        vrp_res = vrp_runner.solve_instance(vrp_inst, time_limit=time_limit_vrp, threads=threads)

        if vrp_res.has_solution and vrp_res.objective is not None:
            routing_objective = float(vrp_res.objective)
        else:
            # Propagate failure from VRP stage
            t1 = perf_counter()
            sol = GroupedHeuristicSolution(
                packing=[asdict(p) for p in packing_rows],
                grouping=asdict(grouping),
                vrp_instance=vrp_inst.to_dict() if vrp_inst else None,
                vrp_result={
                    "status": vrp_res.status,
                    "has_solution": vrp_res.has_solution,
                    "objective": vrp_res.objective,
                    "time": vrp_res.time,
                    "solution": vrp_res.solution,
                } if vrp_res else None,
                objective_breakdown={
                    "fixed_cost": fixed_cost,
                    "routing_objective": None,
                    "total_objective": None,
                },
            )
            return SolveResult(
                status=vrp_res.status if vrp_res else "UNKNOWN",
                has_solution=False,
                objective=None,
                solution=asdict(sol),
                time=float(t1 - t0),
                raw_result={"packing": packing_rows, "grouping": grouping, "vrp_result": vrp_res},
            )

    total_objective = float(fixed_cost) + float(routing_objective)

    t1 = perf_counter()

    sol = GroupedHeuristicSolution(
        packing=[asdict(p) for p in packing_rows],
        grouping=asdict(grouping),
        vrp_instance=vrp_inst.to_dict() if vrp_inst else None,
        vrp_result={
            "status": vrp_res.status,
            "has_solution": vrp_res.has_solution,
            "objective": vrp_res.objective,
            "time": vrp_res.time,
            "solution": vrp_res.solution,
        } if vrp_res else None,
        objective_breakdown={
            "fixed_cost": fixed_cost,
            "routing_objective": routing_objective,
            "total_objective": total_objective,
        },
    )

    # We return a SolveResult for consistent downstream JSON/CSV tooling.
    return SolveResult(
        status=(vrp_res.status if vrp_res is not None else "SATISFIED"),
        has_solution=True,
        objective=total_objective,
        solution=asdict(sol),
        time=float(t1 - t0),
        raw_result={"packing": packing_rows, "grouping": grouping, "vrp_result": vrp_res},
    )


# -----------------------------
# Experiment-style runner (like other models)
# -----------------------------

def run_grouped_heuristic_over_seeds(
    *,
    instances: Sequence[BPCSDVRPInstance],
    bpp_model_path: PathLike,
    vrp_model_path: PathLike,
    solver_name: str = "cp-sat",
    threads: Optional[int] = 24,
    time_limit_bpp_per_customer: Optional[float] = None,
    time_limit_vrp: Optional[float] = None,
    treat_equal_capacity_as_fixed: bool = False,
    fallback_bpp: str = "items_ub",
) -> List[SolveResult]:
    """
    Convenience wrapper when you already have a list of instances generated with different seeds.
    Returns a list of SolveResults (one per instance), with timing measured per instance.
    """
    results: List[SolveResult] = []
    for inst in instances:
        res = solve_bpcsdvrp_grouped_heuristic(
            inst=inst,
            bpp_model_path=bpp_model_path,
            vrp_model_path=vrp_model_path,
            solver_name=solver_name,
            threads=threads,
            time_limit_bpp_per_customer=time_limit_bpp_per_customer,
            time_limit_vrp=time_limit_vrp,
            treat_equal_capacity_as_fixed=treat_equal_capacity_as_fixed,
            fallback_bpp=fallback_bpp,
        )
        results.append(res)
    return results
