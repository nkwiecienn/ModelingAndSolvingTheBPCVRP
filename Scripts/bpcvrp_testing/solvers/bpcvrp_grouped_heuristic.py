from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from bpcvrp_testing.solvers.minizinc_runner import MiniZincRunner, SolveResult
from bpcvrp_testing.instances.grouped_vrp_instance import GroupedVRPInstance

PathLike = Union[str, Path]


@dataclass
class PalletisationStats:
    pallets_per_customer: List[int]                 # p_c
    full_trips_per_customer: List[int]              # floor(p_c / Capacity)
    remainder_per_customer: List[int]               # p_c % Capacity
    fixed_cost: int
    remaining_customer_ids: List[int]               # original customers kept as nodes
    remaining_demands: List[int]                    # demand for each remaining node (same order)


@dataclass
class GroupedHeuristicResult:
    """
    Result of the heuristic pipeline:

    (1) solve BPP per customer -> pallets p_c
    (2) split p_c into full trips + remainder
    (3) solve VRP on remainder nodes only, with fixedCost added

    The VRP objective already includes fixedCost (if the VRP model is written
    in that way). We keep fixedCost separately for reporting/validation.
    """
    palletisation: PalletisationStats
    grouped_instance: Optional[GroupedVRPInstance]
    vrp_result: Optional[SolveResult]

    @property
    def status(self) -> str:
        if self.vrp_result is None:
            return "NO_VRP"
        return self.vrp_result.status

    @property
    def objective(self) -> Optional[float]:
        if self.vrp_result is None:
            return float(self.palletisation.fixed_cost)
        return self.vrp_result.objective


def _extract_bpp_objective(res: SolveResult) -> Optional[int]:
    """
    Robustly extract number of pallets from a BPP solve result.

    Accepts either:
      - res.objective (preferred)
      - solution['nBins']  (common in your BPP model)
      - solution['objective'] (if you used an explicit objective var)
    """
    if res.objective is not None:
        return int(round(res.objective))

    sol = res.solution or {}
    for key in ("nBins", "objective"):
        if key in sol and sol[key] is not None:
            try:
                return int(sol[key])
            except Exception:
                pass
    return None


def solve_bpp_for_customer(
    bpp_runner: MiniZincRunner,
    sizes: Sequence[int],
    bin_capacity: int,
    time_limit: Optional[float] = None,
    fallback: str = "volume_lb",
) -> int:
    """
    Solve the 1D bin packing model for a single customer order.

    Parameters
    ----------
    sizes:
        Item sizes (positive ints). Zero padding should be removed by caller.
    bin_capacity:
        Capacity of one pallet/bin.
    fallback:
        What to do if the BPP solve fails:
          - 'volume_lb' : ceil(sum(sizes)/bin_capacity)
          - 'worst'     : len(sizes)  (one item per pallet)

    Returns
    -------
    int: number of pallets (bins) used.
    """
    sizes = [int(s) for s in sizes if int(s) > 0]
    if not sizes:
        return 0

    data = {
        "n": len(sizes),
        "capacity": int(bin_capacity),
        "size": list(sizes),
    }

    res = bpp_runner.solve(data, time_limit=time_limit)
    pallets = _extract_bpp_objective(res)

    if pallets is not None:
        return pallets

    # fallback
    if fallback == "worst":
        return len(sizes)

    # default: volume lower bound
    return int(ceil(sum(sizes) / float(bin_capacity)))


def palletise_and_group(
    N: int,
    Capacity: int,
    Distance: List[List[int]],
    ItemsPerCustomer: Sequence[int],
    SizesOfItems: Sequence[Sequence[int]],
    binCapacity: int,
    bpp_model_path: PathLike,
    solver_name: str = "chuffed",
    time_limit_per_customer: Optional[float] = None,
    fallback: str = "volume_lb",
) -> PalletisationStats:
    """
    Run BPP per customer, then group pallets into:
      - full trips of size Capacity (counted into fixedCost)
      - one remainder node (if remainder > 0)

    Returns stats plus the reduced node list and demands.
    """
    bpp_runner = MiniZincRunner(bpp_model_path, solver_name=solver_name)

    pallets_per_customer: List[int] = []
    full_trips_per_customer: List[int] = []
    remainder_per_customer: List[int] = []

    fixed_cost = 0
    remaining_customer_ids: List[int] = []
    remaining_demands: List[int] = []

    for c in range(1, N + 1):
        k = int(ItemsPerCustomer[c - 1])
        row = list(SizesOfItems[c - 1])[:k]
        pallets = solve_bpp_for_customer(
            bpp_runner=bpp_runner,
            sizes=row,
            bin_capacity=binCapacity,
            time_limit=time_limit_per_customer,
            fallback=fallback,
        )

        pallets_per_customer.append(pallets)

        full_trips = pallets // Capacity
        rem = pallets % Capacity
        full_trips_per_customer.append(full_trips)
        remainder_per_customer.append(rem)

        if full_trips > 0:
            # each full trip is depot -> customer -> depot
            # Distance matrix convention: row/col 0 is depot, 1..N are customers
            fixed_cost += full_trips * (2 * int(Distance[0][c]))

        if rem > 0:
            remaining_customer_ids.append(c)
            remaining_demands.append(rem)

    return PalletisationStats(
        pallets_per_customer=pallets_per_customer,
        full_trips_per_customer=full_trips_per_customer,
        remainder_per_customer=remainder_per_customer,
        fixed_cost=fixed_cost,
        remaining_customer_ids=remaining_customer_ids,
        remaining_demands=remaining_demands,
    )


def build_grouped_vrp_instance(
    Capacity: int,
    original_distance: List[List[int]],
    remaining_customer_ids: List[int],
    remaining_demands: List[int],
    fixedCost: int,
    nbVehicles: Optional[int] = None,
    name: Optional[str] = None,
) -> GroupedVRPInstance:
    """
    Build a reduced CVRP instance over the remaining nodes.

    - Each remaining node corresponds to one original customer id.
    - Distance matrix is extracted as a submatrix of the original.
    """
    assert len(remaining_customer_ids) == len(remaining_demands)

    N_rem = len(remaining_customer_ids)
    if nbVehicles is None:
        # Safe upper bound in the same spirit as your benchmark VRP model
        nbVehicles = max(1, N_rem)

    # indices in the original matrix: 0 = depot, customer c is index c
    idx = [0] + remaining_customer_ids

    Distance_rem: List[List[int]] = []
    for i in idx:
        Distance_rem.append([int(original_distance[i][j]) for j in idx])

    return GroupedVRPInstance(
        N=N_rem,
        Capacity=int(Capacity),
        nbVehicles=int(nbVehicles),
        Demand=[int(d) for d in remaining_demands],
        Distance=Distance_rem,
        fixedCost=int(fixedCost),
        origCustomerOfNode=list(remaining_customer_ids),
        name=name,
    )


def solve_grouped_orders_vrp(
    grouped_instance: GroupedVRPInstance,
    vrp_model_path: PathLike,
    solver_name: str = "chuffed",
    time_limit: Optional[float] = None,
) -> SolveResult:
    """
    Solve the reduced VRP model that includes fixedCost.

    The MiniZinc model is expected to accept:
      N, Capacity, nbVehicles, Demand, Distance, fixedCost
    """
    runner = MiniZincRunner(vrp_model_path, solver_name=solver_name)
    return runner.solve_instance(grouped_instance, time_limit=time_limit)


def solve_bpcvrp_grouped_heuristic(
    instance_obj: Any,
    bpp_model_path: PathLike,
    vrp_grouped_model_path: PathLike,
    solver_name: str = "chuffed",
    time_limit_per_customer: Optional[float] = None,
    time_limit_vrp: Optional[float] = None,
    fallback: str = "volume_lb",
    nbVehicles: Optional[int] = None,
) -> GroupedHeuristicResult:
    """
    End-to-end heuristic:

      (a) Palletise each customer by running BPP in MiniZinc.
      (b) Split pallets into full trips + one remainder node.
      (c) Solve a classical VRP on the remainder nodes, with fixedCost added.

    Requirements for `instance_obj`:
      - N, Capacity, Distance
      - ItemsPerCustomer, SizesOfItems, binCapacity

    `nbVehicles`:
      - if None, uses N_remaining as a safe upper bound (same as your CVRP model style).
    """
    N = int(instance_obj.N)
    Capacity = int(instance_obj.Capacity)
    Distance = instance_obj.Distance
    ItemsPerCustomer = instance_obj.ItemsPerCustomer
    SizesOfItems = instance_obj.SizesOfItems
    binCapacity = int(instance_obj.binCapacity)

    stats = palletise_and_group(
        N=N,
        Capacity=Capacity,
        Distance=Distance,
        ItemsPerCustomer=ItemsPerCustomer,
        SizesOfItems=SizesOfItems,
        binCapacity=binCapacity,
        bpp_model_path=bpp_model_path,
        solver_name=solver_name,
        time_limit_per_customer=time_limit_per_customer,
        fallback=fallback,
    )

    # If everything became a fixed full-trip, no VRP remains.
    if len(stats.remaining_customer_ids) == 0:
        return GroupedHeuristicResult(
            palletisation=stats,
            grouped_instance=None,
            vrp_result=None,
        )

    grouped_inst = build_grouped_vrp_instance(
        Capacity=Capacity,
        original_distance=Distance,
        remaining_customer_ids=stats.remaining_customer_ids,
        remaining_demands=stats.remaining_demands,
        fixedCost=stats.fixed_cost,
        nbVehicles=nbVehicles,
        name=getattr(instance_obj, "name", None),
    )

    vrp_res = solve_grouped_orders_vrp(
        grouped_instance=grouped_inst,
        vrp_model_path=vrp_grouped_model_path,
        solver_name=solver_name,
        time_limit=time_limit_vrp,
    )

    return GroupedHeuristicResult(
        palletisation=stats,
        grouped_instance=grouped_inst,
        vrp_result=vrp_res,
    )
