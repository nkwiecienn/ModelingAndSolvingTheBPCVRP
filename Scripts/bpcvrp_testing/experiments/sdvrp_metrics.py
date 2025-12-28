
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..instances.sdvrp_instance import SDVRPInstance


def _as_list(x: Any) -> List[Any]:
    """Convert MiniZinc array-like objects to plain Python lists."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    try:
        return list(x)
    except TypeError:
        return [x]


def compute_sdvrp_metrics(instance: SDVRPInstance, solution: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract SDVRP-specific metrics from a MiniZinc solution.

    Assumes the model outputs (at least):
      - successor: array[NODES] of int
      - delivered: array[NODES] of int
      - vehicle:   array[NODES] of int
    """

    succ = _as_list(solution.get("successor"))
    delivered = _as_list(solution.get("delivered"))
    veh = _as_list(solution.get("vehicle"))

    if not succ or not delivered:
        return {"sd_metrics_available": False}

    N = instance.N
    mv = instance.maxVisitsPerCustomer
    nb_copies = N * mv

    # Node indices in the model are 1..lastNode; lists are 0-based.
    def node_val(arr: List[Any], node: int) -> Any:
        return arr[node - 1]

    active_copies: List[int] = [n for n in range(1, nb_copies + 1) if int(node_val(succ, n)) != n]

    # Delivery per original customer
    delivered_per_customer = [0] * N
    visits_per_customer = [0] * N

    for n in active_copies:
        c = 1 + ((n - 1) // mv)          # original customer index (1..N)
        q = int(node_val(delivered, n))
        if q > 0:
            delivered_per_customer[c - 1] += q
            visits_per_customer[c - 1] += 1

    demand_ok = all(delivered_per_customer[i] == instance.Demand[i] for i in range(N))

    split_customers = sum(1 for v in visits_per_customer if v >= 2)
    served_customers = sum(1 for v in visits_per_customer if v >= 1)

    # Vehicles used = those assigned to at least one active copy.
    used_vehicles = set()
    if veh:
        for n in active_copies:
            used_vehicles.add(int(node_val(veh, n)))
    n_used_vehicles = len(used_vehicles)

    return {
        "sd_metrics_available": True,
        "n_active_copies": len(active_copies),
        "n_served_customers": served_customers,
        "n_split_customers": split_customers,
        "max_visits_customer": max(visits_per_customer) if visits_per_customer else 0,
        "avg_visits_customer": (sum(visits_per_customer) / N) if N else 0.0,
        "n_used_vehicles": n_used_vehicles,
        "demand_satisfied": demand_ok,
        "total_demand": int(sum(instance.Demand)),
        "total_delivered_active": int(sum(delivered_per_customer)),
    }
