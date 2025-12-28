from __future__ import annotations

from math import ceil
from typing import Optional

import random

from .vrp_generator import generate_random_vrp
from ..instances.sdvrp_instance import SDVRPInstance


def generate_random_sdvrp(
    n_customers: int,
    *,
    vehicle_capacity: int,
    demand_min: int,
    demand_max: int,
    maxVisitsPerCustomer: int = 2,
    nbVehicles: Optional[int] = None,
    fraction_oversized: float = 0.3,
    oversized_min_factor: float = 1.2,
    oversized_max_factor: float = 2.5,
    ensure_feasible: bool = True,
    # Forwarded to generate_random_vrp for geometry
    area_size: float = 100.0,
    instance_type: str = "mixed",
    n_clusters: int = 3,
    cluster_std_fraction: float = 0.1,
    mixed_uniform_fraction: float = 0.3,
    seed: Optional[int] = None,
) -> SDVRPInstance:
    """
    Generate a random Split-Delivery CVRP instance (SDVRP).

    Compared to `generate_random_vrp`, this generator intentionally creates
    customers with demand that may exceed vehicle capacity, so that split
    deliveries are meaningful.

    Notes
    -----
    - The SDVRP MiniZinc model requires two additional parameters:
        * nbVehicles
        * maxVisitsPerCustomer
    - If `ensure_feasible=True`, demands are clipped so that:
        Demand[c] <= maxVisitsPerCustomer * vehicle_capacity
      (otherwise the instance would be infeasible under the chosen visit limit).
    - If `nbVehicles` is not provided, it is set to the minimum number of vehicles
      required by capacity: ceil(total_demand / vehicle_capacity).
    """

    if vehicle_capacity <= 0:
        raise ValueError("vehicle_capacity must be positive")
    if maxVisitsPerCustomer <= 0:
        raise ValueError("maxVisitsPerCustomer must be positive")
    if not (0.0 <= fraction_oversized <= 1.0):
        raise ValueError("fraction_oversized must be in [0, 1]")
    if oversized_min_factor <= 1.0:
        raise ValueError("oversized_min_factor should be > 1.0 to create split-needed demands")
    if oversized_max_factor < oversized_min_factor:
        raise ValueError("oversized_max_factor must be >= oversized_min_factor")

    rng = random.Random(seed)

    base = generate_random_vrp(
        n_customers=n_customers,
        area_size=area_size,
        demand_min=demand_min,
        demand_max=demand_max,
        vehicle_capacity=vehicle_capacity,   # IMPORTANT: keep capacity fixed
        instance_type=instance_type,
        n_clusters=n_clusters,
        cluster_std_fraction=cluster_std_fraction,
        mixed_uniform_fraction=mixed_uniform_fraction,
        seed=seed,
    )

    demands = list(base.Demand)

    # Decide how many customers should require splitting.
    k = int(round(fraction_oversized * n_customers))
    if fraction_oversized > 0 and k == 0:
        k = 1

    oversized_customers = rng.sample(range(n_customers), k) if k > 0 else []

    for idx in oversized_customers:
        target = int(round(rng.uniform(oversized_min_factor, oversized_max_factor) * vehicle_capacity))
        if ensure_feasible:
            target = min(target, maxVisitsPerCustomer * vehicle_capacity)
        # If we can, enforce strictly > capacity
        if target <= vehicle_capacity and (maxVisitsPerCustomer * vehicle_capacity) > vehicle_capacity:
            target = min(vehicle_capacity + 1, maxVisitsPerCustomer * vehicle_capacity)
        demands[idx] = max(demand_min, target)

    if ensure_feasible:
        max_allowed = maxVisitsPerCustomer * vehicle_capacity
        demands = [min(d, max_allowed) for d in demands]

    total_demand = sum(demands)
    min_vehicles = max(1, ceil(total_demand / vehicle_capacity))

    if nbVehicles is None:
        nbVehicles_final = min_vehicles
    else:
        nbVehicles_final = int(nbVehicles)
        if nbVehicles_final < min_vehicles:
            raise ValueError(
                f"nbVehicles={nbVehicles_final} is too small for total demand {total_demand} "
                f"and capacity {vehicle_capacity} (minimum required: {min_vehicles})."
            )

    name = f"sdvrp_N{n_customers}_cap{vehicle_capacity}_mv{maxVisitsPerCustomer}_seed{seed}"

    return SDVRPInstance(
        N=base.N,
        Capacity=vehicle_capacity,
        Demand=demands,
        Distance=[list(r) for r in base.Distance],
        nbVehicles=nbVehicles_final,
        maxVisitsPerCustomer=maxVisitsPerCustomer,
        name=name,
    )
