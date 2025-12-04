from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class BPCVRPInstance:
    # VRP part
    N: int                               # number of customers (excluding depot)
    Capacity: int                        # vehicle capacity (in pallets)
    Distance: List[List[int]]           # (N+1)x(N+1), index 0=depot, 1..N=customers

    # BPP part (per customer)
    ItemsPerCustomer: List[int]         # length N, number of items per customer i=1..N
    maxItemsPerCustomer: int            # max(ItemsPerCustomer)
    binCapacity: int                    # capacity of a single pallet
    SizesOfItems: List[List[int]]       # N x maxItemsPerCustomer

    # Optional instance name (for logs / experiments)
    name: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        """Return a dict of input data for the BPCVRP MiniZinc model.

        The model is expected to accept parameters:
            int: N;
            int: Capacity;
            array[0..N, 0..N] of int: Distance;
            array[1..N] of int: ItemsPerCustomer;
            int: maxItemsPerCustomer;
            int: binCapacity;
            array[1..N, 1..maxItemsPerCustomer] of int: SizesOfItems;
        """
        # Basic dimension validation (to catch errors early)

        return {
            "N": self.N,
            "Capacity": self.Capacity,
            "Distance": [list(r) for r in self.Distance],
            "ItemsPerCustomer": list(self.ItemsPerCustomer),
            "maxItemsPerCustomer": self.maxItemsPerCustomer,
            "binCapacity": self.binCapacity,
            "SizesOfItems": [list(r) for r in self.SizesOfItems],
        }


    def to_dzn(self) -> str:
        """Return a .dzn text compatible with the BPCVRP model.

        Example output structure:

            N = ...;
            Capacity = ...;
            ItemsPerCustomer = [ ... ];
            maxItemsPerCustomer = ...;
            binCapacity = ...;
            SizesOfItems = [|
              ...
            | ... |];
            Distance = [|
              ...
            | ... |];
        """
        lines: List[str] = []

        lines.append(f"N = {self.N};")
        lines.append(f"Capacity = {self.Capacity};")

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
