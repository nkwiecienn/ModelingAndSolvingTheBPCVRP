from __future__ import annotations

from math import floor, ceil
from typing import List, Optional
import random

from ..instances.vrp_instance import VRPInstance
from ..instances.bpcvrp_instance import BPCVRPInstance
from .vrp_generator import generate_random_vrp


def generate_random_bpcvrp(
    # ----- VRP part -----
    n_customers: int,
    area_size: float = 100.0,
    demand_min: int = 1,
    demand_max: int = 10,
    vehicle_capacity: Optional[int] = None,
    vehicle_capacity_factor: float = 1.0,
    target_vehicles: Optional[int] = None,
    instance_type: str = "uniform",          # 'uniform' | 'clustered' | 'mixed'
    n_clusters: int = 3,
    cluster_std_fraction: float = 0.1,
    mixed_uniform_fraction: float = 0.3,

    # ----- BPP part (per customer) -----
    bin_capacity: int = 50,                  # "pallet" capacity
    min_item_ratio: float = 0.2,             # items in [0.2 * bin_capacity, 0.8 * bin_capacity]
    max_item_ratio: float = 0.8,
    min_items_per_customer: int = 3,
    max_items_per_customer: int = 10,

    # ----- randomness -----
    seed: Optional[int] = None,

) -> BPCVRPInstance:
    """Generate a random integrated BPCVRP instance.

    Procedure:
    1) Generate a standard VRP (Demand is not used in the MiniZinc model):
       - N customers,
       - depot at the center,
       - Distance matrix using EUC_2D,
       - Capacity (in pallets) computed from parameters or taken directly.

    2) For each customer i = 1..N:
       - sample ItemsPerCustomer[i] from [min_items_per_customer, max_items_per_customer],
       - sample item sizes from [min_item_ratio * bin_capacity, max_item_ratio * bin_capacity],
       - sizes are integers in [1, bin_capacity].

    3) Build and return a `BPCVRPInstance` containing:
       - ItemsPerCustomer (array[1..N] of int),
       - maxItemsPerCustomer,
       - SizesOfItems (array[1..N, 1..maxItemsPerCustomer] of int),
       - other VRP parameters produced by `generate_random_vrp`.

    VRP parameters match those of `generate_random_vrp`; BPP parameters control
    the item-pack structure per customer.
    """
    rng = random.Random(seed)

    vrp_seed = rng.randint(0, 2**31 - 1)
    vrp: VRPInstance = generate_random_vrp(
        n_customers=n_customers,
        area_size=area_size,
        demand_min=demand_min,
        demand_max=demand_max,
        vehicle_capacity=vehicle_capacity,
        vehicle_capacity_factor=vehicle_capacity_factor,
        target_vehicles=target_vehicles,
        instance_type=instance_type,
        n_clusters=n_clusters,
        cluster_std_fraction=cluster_std_fraction,
        mixed_uniform_fraction=mixed_uniform_fraction,
        seed=vrp_seed,
    )

    N = vrp.N
    Capacity = vrp.Capacity
    Distance = vrp.Distance

    min_size = max(1, floor(min_item_ratio * bin_capacity))
    max_size = min(bin_capacity, ceil(max_item_ratio * bin_capacity))
    if min_size > max_size:
        min_size = max_size = 1

    ItemsPerCustomer: List[int] = []
    for _ in range(N):
        k = rng.randint(min_items_per_customer, max_items_per_customer)
        ItemsPerCustomer.append(k)

    maxItemsPerCustomer = max(ItemsPerCustomer)

    SizesOfItems: List[List[int]] = []
    for k in ItemsPerCustomer:
        row: List[int] = [
            rng.randint(min_size, max_size) for _ in range(k)
        ]
        row.sort(reverse=True)
        if k < maxItemsPerCustomer:
            row.extend([0] * (maxItemsPerCustomer - k))
        SizesOfItems.append(row)

    inst = BPCVRPInstance(
        N=N,
        Capacity=Capacity,
        Distance=Distance,
        ItemsPerCustomer=ItemsPerCustomer,
        maxItemsPerCustomer=maxItemsPerCustomer,
        binCapacity=bin_capacity,
        SizesOfItems=SizesOfItems,
        name=None,
    )

    return inst
