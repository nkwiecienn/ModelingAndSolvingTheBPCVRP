from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BPCSDVRPInstance:
    """
    Integrated instance for:
      - per-customer Bin Packing (items -> pallets)
      - Split-Delivery CVRP (deliver pallets, allowing multiple visits per customer)

    Conventions (consistent with your existing instances):
      - N: number of customers (excluding depot)
      - Distance: (N+1)x(N+1) matrix, index 0 = depot, 1..N = customers
      - Capacity: vehicle capacity (in pallets)
      - binCapacity: pallet capacity for packing (in item-size units)
    """

    # VRP part
    N: int
    Capacity: int
    Distance: List[List[int]]

    # Split-delivery parameters
    nbVehicles: int
    maxVisitsPerCustomer: int

    # Packing part (per customer)
    ItemsPerCustomer: List[int]          # length N
    maxItemsPerCustomer: int             # max(ItemsPerCustomer)
    binCapacity: int                     # pallet capacity (in item-size units)
    SizesOfItems: List[List[int]]        # N x maxItemsPerCustomer (0-padded)

    # Optional instance name (for logs / experiments)
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a dict of input data for the BP-SDVRP MiniZinc model."""
        return {
            "N": self.N,
            "Capacity": self.Capacity,
            "Distance": [list(r) for r in self.Distance],

            "nbVehicles": self.nbVehicles,
            "maxVisitsPerCustomer": self.maxVisitsPerCustomer,

            "ItemsPerCustomer": list(self.ItemsPerCustomer),
            "maxItemsPerCustomer": self.maxItemsPerCustomer,
            "binCapacity": self.binCapacity,
            "SizesOfItems": [list(r) for r in self.SizesOfItems],
        }

    def to_dzn(self) -> str:
        """Return a .dzn text compatible with the BP-SDVRP model."""
        lines: List[str] = []

        lines.append(f"N = {self.N};")
        lines.append(f"Capacity = {self.Capacity};")
        lines.append(f"nbVehicles = {self.nbVehicles};")
        lines.append(f"maxVisitsPerCustomer = {self.maxVisitsPerCustomer};")

        ipc_str = ", ".join(str(x) for x in self.ItemsPerCustomer)
        lines.append(f"ItemsPerCustomer = [{ipc_str}];")
        lines.append(f"maxItemsPerCustomer = {self.maxItemsPerCustomer};")
        lines.append(f"binCapacity = {self.binCapacity};")

        lines.append("SizesOfItems = [|")
        for i, row in enumerate(self.SizesOfItems, start=1):
            row_str = ", ".join(str(v) for v in row)
            prefix = "  " if i == 1 else "| "
            lines.append(f"{prefix}{row_str}")
        lines.append("|];")

        lines.append("Distance = [|")
        for i, row in enumerate(self.Distance):
            row_str = ", ".join(str(d) for d in row)
            prefix = "  " if i == 0 else "| "
            lines.append(f"{prefix}{row_str}")
        lines.append("|];")

        return "\n".join(lines) + "\n"
