
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .vrp_instance import VRPInstance


@dataclass
class SDVRPInstance:
    """
    Split-Delivery CVRP instance wrapper.

    This keeps the same core data as `VRPInstance` (N, Capacity, Demand, Distance),
    and adds the parameters required by the split-delivery MiniZinc model:
      - nbVehicles            (upper bound on number of vehicles / routes)
      - maxVisitsPerCustomer  (maximum number of allowed visits per customer)

    The goal is to keep your existing CVRP tooling intact while enabling SDVRP
    experiments by swapping only the instance class + model file.
    """
    # Core CVRP data
    N: int
    Capacity: int
    Demand: List[int]
    Distance: List[List[int]]  # (N+1)x(N+1) matrix (depot + customers)

    # SD-specific controls
    nbVehicles: int
    maxVisitsPerCustomer: int

    # Optional metadata (used by batch_runner for nicer filenames)
    name: Optional[str] = None

    @classmethod
    def from_vrp(
        cls,
        base: VRPInstance,
        nbVehicles: int,
        maxVisitsPerCustomer: int,
        name: Optional[str] = None,
    ) -> "SDVRPInstance":
        return cls(
            N=base.N,
            Capacity=base.Capacity,
            Demand=list(base.Demand),
            Distance=[list(r) for r in base.Distance],
            nbVehicles=int(nbVehicles),
            maxVisitsPerCustomer=int(maxVisitsPerCustomer),
            name=name,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "N": self.N,
            "Capacity": self.Capacity,
            "Demand": list(self.Demand),
            "Distance": [list(row) for row in self.Distance],
            "nbVehicles": int(self.nbVehicles),
            "maxVisitsPerCustomer": int(self.maxVisitsPerCustomer),
        }

    def to_dzn(self) -> str:
        """Optional helper: export as .dzn (handy for debugging)."""
        lines: List[str] = []
        lines.append(f"N = {self.N};")
        lines.append(f"Capacity = {self.Capacity};")
        lines.append(f"nbVehicles = {self.nbVehicles};")
        lines.append(f"maxVisitsPerCustomer = {self.maxVisitsPerCustomer};")

        demand_str = ", ".join(str(d) for d in self.Demand)
        lines.append(f"Demand = [{demand_str}];")

        lines.append("Distance = [|")
        for i, row in enumerate(self.Distance):
            row_str = ", ".join(str(x) for x in row)
            prefix = "  " if i == 0 else "| "
            lines.append(f"{prefix}{row_str}")
        lines.append("|];")

        return "\n".join(lines) + "\n"
