from __future__ import annotations

from typing import List, Tuple, Optional
from math import sqrt
import random

from ..instances.vrp_instance import VRPInstance


def _euc_2d(p: Tuple[float, float], q: Tuple[float, float]) -> int:
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return int(sqrt(dx * dx + dy * dy) + 0.5)


def generate_random_vrp(
    n_customers: int,
    area_size: float = 100.0,
    demand_min: int = 1,
    demand_max: int = 10,
    vehicle_capacity: Optional[int] = None,
    vehicle_capacity_factor: float = 1.0,
    target_vehicles: Optional[int] = None,
    instance_type: str = "uniform",
    n_clusters: int = 3,
    cluster_std_fraction: float = 0.1,
    mixed_uniform_fraction: float = 0.3,
    seed: Optional[int] = None,
) -> VRPInstance:
    """Generate a random CVRP instance compatible with the MiniZinc model.

    Assumptions
    -----------
    - depot is placed at the center of the square [0, area_size] x [0, area_size]
    - customers are distributed according to ``instance_type``:
        * 'uniform'   - uniformly across the area
        * 'clustered' - around ``n_clusters`` random centers
        * 'mixed'     - some customers uniform, some clustered
    - demands are sampled from [demand_min, demand_max]
    - Capacity:
        * if ``vehicle_capacity`` is provided, it is used directly
        * otherwise capacity is computed from total demand:
              base_cap = total_demand / (target_vehicles or default)
              Capacity = max(max_demand, round(vehicle_capacity_factor * base_cap))

    Parameters
    ----------
    n_customers : int
        Number of customers (excluding the depot).
    area_size : float
        Side length of the square in which coordinates are sampled.
    demand_min, demand_max : int
        Range of demands per customer.
    vehicle_capacity : int | None
        If provided, use this vehicle capacity directly.
    vehicle_capacity_factor : float
        Multiplier used when calculating capacity from total demand.
    target_vehicles : int | None
        Target number of vehicles for capacity calculation. If None, use
        the heuristic ``max(1, round(n_customers / 10))``.
    instance_type : str
        One of 'uniform', 'clustered' or 'mixed'.
    n_clusters : int
        Number of clusters for 'clustered' / 'mixed' modes.
    cluster_std_fraction : float
        Cluster standard deviation as a fraction of ``area_size`` (e.g. 0.1 → 10%).
    mixed_uniform_fraction : float
        Fraction of 'uniform' customers when ``instance_type`` == 'mixed' (e.g. 0.3 = 30%).
    seed : int | None
        RNG seed for reproducibility.

    Returns
    -------
    VRPInstance
        An instance containing:
        - N        (number of customers),
        - Capacity (vehicle capacity),
        - Demand   (list of length N),
        - Distance ((N+1)x(N+1) matrix with 0=depot, 1..N=customers)
    """

    rng = random.Random(seed)

    depot = (area_size / 2.0, area_size / 2.0)

    cluster_centers: List[Tuple[float, float]] = []
    for _ in range(n_clusters):
        cx = rng.uniform(0.2 * area_size, 0.8 * area_size)
        cy = rng.uniform(0.2 * area_size, 0.8 * area_size)
        cluster_centers.append((cx, cy))

    cluster_std = cluster_std_fraction * area_size

    def sample_uniform() -> Tuple[float, float]:
        return (rng.uniform(0.0, area_size), rng.uniform(0.0, area_size))

    def sample_clustered() -> Tuple[float, float]:
        cx, cy = rng.choice(cluster_centers)
        x = rng.gauss(cx, cluster_std)
        y = rng.gauss(cy, cluster_std)
        x = max(0.0, min(area_size, x))
        y = max(0.0, min(area_size, y))
        return (x, y)

    coords: List[Tuple[float, float]] = []
    for _ in range(n_customers):
        if instance_type == "uniform":
            coords.append(sample_uniform())
        elif instance_type == "clustered":
            coords.append(sample_clustered())
        else:
            if rng.random() < mixed_uniform_fraction:
                coords.append(sample_uniform())
            else:
                coords.append(sample_clustered())

    demands: List[int] = [
        rng.randint(demand_min, demand_max) for _ in range(n_customers)
    ]
    total_demand = sum(demands)
    max_demand = max(demands)

    if vehicle_capacity is not None:
        capacity = int(vehicle_capacity)
        if capacity <= 0:
            raise ValueError(f"vehicle_capacity must be > 0, got {capacity}")
    else:
        if target_vehicles is None:
            target_vehicles = max(1, round(n_customers / 10))

        base_cap = total_demand / float(target_vehicles)
        cap = int(round(vehicle_capacity_factor * base_cap))
        capacity = max(max_demand, cap, 1)

    N = n_customers
    nodes: List[Tuple[float, float]] = [depot] + coords

    distance: List[List[int]] = [[0] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        for j in range(N + 1):
            if i == j:
                distance[i][j] = 0
            else:
                distance[i][j] = _euc_2d(nodes[i], nodes[j])

    return VRPInstance(
        N=N,
        Capacity=capacity,
        Demand=demands,
        Distance=distance,
    )
