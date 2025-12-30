from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GroupedVRPInstance:
    """
    CVRP instance obtained after preprocessing pallet demand:

      - Some pallet groups are full-vehicle (demand == Capacity). These are removed
        from routing and accounted for via `fixedCost`.

      - The remaining groups (each with demand < Capacity) form a standard CVRP
        instance (single visit per node, no split deliveries).

    Data conventions:
      - N: number of remaining nodes (excluding depot)
      - Distance: (N+1)x(N+1) matrix (Python list of lists)
          row/col 0 = depot
          row/col 1..N = remaining nodes
        This matches your existing VRP instances and MiniZinc API usage.

      - origCustomerOfNode: optional mapping of remaining node index (1..N) to
        original customer id (1..N_original). Useful for debugging/plots.
    """
    N: int
    Capacity: int
    nbVehicles: int

    Demand: List[int]                 # length N
    Distance: List[List[int]]         # (N+1)x(N+1)

    fixedCost: int                    # constant depot->customer->depot cost for removed full trips
    origCustomerOfNode: Optional[List[int]] = None

    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "N": self.N,
            "Capacity": self.Capacity,
            "nbVehicles": self.nbVehicles,
            "Demand": list(self.Demand),
            "Distance": [list(r) for r in self.Distance],
            "fixedCost": int(self.fixedCost),
        }

    def to_dzn(self) -> str:
        lines: List[str] = []
        lines.append(f"N = {self.N};")
        lines.append(f"Capacity = {self.Capacity};")
        lines.append(f"nbVehicles = {self.nbVehicles};")
        lines.append(f"fixedCost = {int(self.fixedCost)};")

        demand_str = ", ".join(str(d) for d in self.Demand)
        lines.append(f"Demand = [{demand_str}];")

        lines.append("Distance = [|")
        for i, row in enumerate(self.Distance):
            row_str = ", ".join(str(x) for x in row)
            prefix = "  " if i == 0 else "| "
            lines.append(f"{prefix}{row_str}")
        lines.append("|];")

        return "\n".join(lines) + "\n"
