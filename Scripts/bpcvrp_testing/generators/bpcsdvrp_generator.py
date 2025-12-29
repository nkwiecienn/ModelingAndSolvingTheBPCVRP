from __future__ import annotations

from math import ceil, floor
from typing import List, Optional
import random

from ..instances.vrp_instance import VRPInstance
from ..instances.bpcsdvrp_instance import BPCSDVRPInstance
from .vrp_generator import generate_random_vrp


def _lb_pallets_for_customer(sizes: List[int], bin_capacity: int) -> int:
    """Lower bound on pallets needed: ceil(total_size / bin_capacity)."""
    total = sum(v for v in sizes if v > 0)
    return int(ceil(total / bin_capacity)) if total > 0 else 0


def generate_random_bpcsdvrp(
    # ----- geometry / distance part (reuses VRP generator) -----
    n_customers: int,
    area_size: float = 100.0,
    instance_type: str = "uniform",          # 'uniform' | 'clustered' | 'mixed'
    n_clusters: int = 3,
    cluster_std_fraction: float = 0.1,
    mixed_uniform_fraction: float = 0.3,

    # ----- SD parameters -----
    maxVisitsPerCustomer: int = 3,
    nbVehicles: Optional[int] = None,        # if None -> computed below
    target_vehicles: Optional[int] = None,   # used if nbVehicles is None
    vehicle_capacity: Optional[int] = None,  # Capacity in pallets; if None -> computed
    vehicle_capacity_factor: float = 1.0,

    # ----- BPP part (per customer) -----
    bin_capacity: int = 50,                  # pallet capacity (item-size units)
    min_item_ratio: float = 0.2,
    max_item_ratio: float = 0.8,
    min_items_per_customer: int = 3,
    max_items_per_customer: int = 10,
    maxItemsPerCustomer: Optional[int] = None,  # if None -> max of sampled k's

    # ----- forcing split cases -----
    fraction_split_customers: float = 0.25,  # fraction of customers with LB pallets > Capacity
    split_min_extra_pallets: int = 1,        # enforce LB >= Capacity + this value

    # ----- randomness -----
    seed: Optional[int] = None,
) -> BPCSDVRPInstance:
    """
    Generate a random BP–SDVRP instance.

    Design goal
    -----------
    For a meaningful split-delivery benchmark, some customers should *require*
    splitting. We enforce this by shaping a fraction of customers so that the
    *volume lower bound* on pallets exceeds the vehicle pallet capacity.

    Notes
    -----
    - The routing Demand is NOT generated directly. The MiniZinc model derives it
      by packing items into pallets (bins).
    - We still reuse `generate_random_vrp` for the distance matrix (geometry).
      Its own Demand output is ignored.
    """
    if maxVisitsPerCustomer <= 0:
        raise ValueError("maxVisitsPerCustomer must be >= 1")

    rng = random.Random(seed)

    # ------------------------------------------------------------
    # 1) Generate per-customer items (sizes), 0-padded later
    # ------------------------------------------------------------
    min_size = max(1, floor(min_item_ratio * bin_capacity))
    max_size = min(bin_capacity, ceil(max_item_ratio * bin_capacity))
    if min_size > max_size:
        min_size = max_size = 1

    ItemsPerCustomer: List[int] = []
    raw_sizes: List[List[int]] = []

    for _ in range(n_customers):
        k = rng.randint(min_items_per_customer, max_items_per_customer)
        ItemsPerCustomer.append(k)
        row = [rng.randint(min_size, max_size) for _ in range(k)]
        row.sort(reverse=True)
        raw_sizes.append(row)

    m = maxItemsPerCustomer if maxItemsPerCustomer is not None else max(ItemsPerCustomer)
    if m <= 0:
        m = 1

    # Lower bounds (by volume)
    lb_pallets = [_lb_pallets_for_customer(row, bin_capacity) for row in raw_sizes]
    total_lb = sum(lb_pallets)

    # ------------------------------------------------------------
    # 2) Decide Capacity (in pallets) if not provided
    # ------------------------------------------------------------
    if vehicle_capacity is None:
        # Choose a default target vehicles similar to VRP generator
        if target_vehicles is None:
            target_vehicles = max(1, round(n_customers / 10))

        # base cap from lower bounds (not from VRP demands)
        base_cap = total_lb / max(1, target_vehicles)
        cap = max(1, int(round(vehicle_capacity_factor * base_cap)))
        vehicle_capacity = cap

    Capacity = int(vehicle_capacity)

    # ------------------------------------------------------------
    # 3) Enforce a fraction of customers requiring split deliveries
    #    (LB pallets > Capacity), but remain feasible under visit cap.
    # ------------------------------------------------------------
    n_force = int(round(fraction_split_customers * n_customers))
    n_force = max(0, min(n_customers, n_force))

    if n_force > 0:
        candidates = list(range(n_customers))
        rng.shuffle(candidates)
        force_idx = candidates[:n_force]

        # Upper feasible LB pallets per customer under maxVisits
        max_lb_feasible = maxVisitsPerCustomer * Capacity

        for c in force_idx:
            # choose desired LB pallets: at least Capacity + split_min_extra_pallets
            lb_min = Capacity + max(1, split_min_extra_pallets)
            lb_max = max_lb_feasible
            if lb_min > lb_max:
                # cannot force a split for this capacity/visit limit; skip
                continue

            desired_lb = rng.randint(lb_min, lb_max)

            # Pick item count; ensure we can reach desired volume
            k = rng.randint(min_items_per_customer, max_items_per_customer)
            ItemsPerCustomer[c] = k

            # Target total size that gives exactly desired_lb by volume:
            # total in ((desired_lb-1)*binCap, desired_lb*binCap]
            target_total = (desired_lb - 1) * bin_capacity + rng.randint(1, bin_capacity)

            # Build sizes by sampling and adjusting last item
            row: List[int] = []
            total = 0
            for _ in range(k):
                if total >= target_total:
                    break
                row.append(rng.randint(min_size, max_size))
                total += row[-1]

            # Ensure we have exactly k items (pad with small ones if needed)
            while len(row) < k:
                row.append(min_size)
                total += min_size

            # Adjust last item so sum == target_total (keep within [1, bin_capacity])
            diff = total - target_total
            if diff > 0:
                # reduce last item
                row[-1] = max(1, row[-1] - diff)
            elif diff < 0:
                # increase last item but not above bin_capacity; if needed, spread over items
                need = -diff
                for t in range(k):
                    add = min(need, bin_capacity - row[t])
                    row[t] += add
                    need -= add
                    if need == 0:
                        break
                # if still need >0, we can't reach exact target; accept larger total
            row.sort(reverse=True)
            raw_sizes[c] = row

    # Recompute m (might have changed k's)
    m = maxItemsPerCustomer if maxItemsPerCustomer is not None else max(ItemsPerCustomer)

    SizesOfItems: List[List[int]] = []
    for k, row in zip(ItemsPerCustomer, raw_sizes):
        r = list(row[:k])
        if k < m:
            r.extend([0] * (m - k))
        SizesOfItems.append(r)

    # ------------------------------------------------------------
    # 4) Decide nbVehicles if not provided
    # ------------------------------------------------------------
    # Use updated lower bounds after forcing splits
    lb_pallets = [_lb_pallets_for_customer(row[:ItemsPerCustomer[i]], bin_capacity)
                  for i, row in enumerate(SizesOfItems)]
    total_lb = sum(lb_pallets)

    if nbVehicles is None:
        if target_vehicles is not None:
            nbVehicles = int(target_vehicles)
        else:
            nbVehicles = max(1, int(ceil(total_lb / max(1, Capacity))))

    nbVehicles = int(nbVehicles)

    # ------------------------------------------------------------
    # 5) Build Distance via VRP generator (demands ignored)
    # ------------------------------------------------------------
    vrp_seed = rng.randint(0, 2**31 - 1)
    vrp: VRPInstance = generate_random_vrp(
        n_customers=n_customers,
        area_size=area_size,
        demand_min=1,
        demand_max=1,
        vehicle_capacity=Capacity,                 # force our Capacity
        vehicle_capacity_factor=1.0,
        target_vehicles=nbVehicles,
        instance_type=instance_type,
        n_clusters=n_clusters,
        cluster_std_fraction=cluster_std_fraction,
        mixed_uniform_fraction=mixed_uniform_fraction,
        seed=vrp_seed,
    )

    inst = BPCSDVRPInstance(
        N=vrp.N,
        Capacity=Capacity,
        Distance=vrp.Distance,
        nbVehicles=nbVehicles,
        maxVisitsPerCustomer=maxVisitsPerCustomer,
        ItemsPerCustomer=ItemsPerCustomer,
        maxItemsPerCustomer=m,
        binCapacity=bin_capacity,
        SizesOfItems=SizesOfItems,
        name=None,
    )

    return inst
