from dataclasses import dataclass
from typing import List, Dict
import math
from pathlib import Path


def _euc2d(p, q) -> int:
    """
    TSPLIB EUC_2D metric
    """
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return int(math.sqrt(dx * dx + dy * dy) + 0.5)


@dataclass
class VRPInstance:
    N: int
    Capacity: int
    Demand: List[int]
    Distance: List[List[int]]

    @classmethod
    def from_txt(cls, path: str) -> "VRPInstance":
        """
        Based on instances from VRPLIB/TSPLIB in format:

            NAME: ...
            COMMENT: ...
            TYPE: CVRP
            DIMENSION: 51
            CAPACITY: 200
            EDGE_WEIGHT_TYPE: EUC_2D
            NODE_COORD_SECTION
            ...
            DEMAND_SECTION
            ...
            DEPOT_SECTION
            ...
            EOF

        Assuming EDGE_WEIGHT_TYPE = EUC_2D.
        Returns:
            N          = DIMENSION - 1 (number of customers without depot)
            Capacity   = CAPACITY
            Demand     = list of customer demands in order 1..N
                         (after reindexing so that depot has index 0)
            Distance   = (N+1)x(N+1) - distances 0..N (0 = depot)
        """
        path_obj = Path(path)

        dimension: int | None = None
        capacity: int | None = None

        coords: Dict[int, tuple[float, float]] = {}
        demands_by_id: Dict[int, int] = {}
        depot_ids: List[int] = []

        section: str | None = None

        with path_obj.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                if ":" in line and section is None:
                    key, val = [s.strip() for s in line.split(":", 1)]
                    if key.upper() == "DIMENSION":
                        dimension = int(val)
                    elif key.upper() == "CAPACITY":
                        capacity = int(val)
                    continue

                upper = line.upper()
                if upper.startswith("NODE_COORD_SECTION"):
                    section = "coords"
                    continue
                if upper.startswith("DEMAND_SECTION"):
                    section = "demand"
                    continue
                if upper.startswith("DEPOT_SECTION"):
                    section = "depot"
                    continue
                if upper.startswith("EOF"):
                    section = None
                    break

                if section == "coords":
                    parts = line.split()
                    if len(parts) >= 3:
                        idx = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        coords[idx] = (x, y)
                elif section == "demand":
                    parts = line.split()
                    if len(parts) >= 2:
                        idx = int(parts[0])
                        dem = int(parts[1])
                        demands_by_id[idx] = dem
                elif section == "depot":
                    if line == "-1":
                        section = None
                    else:
                        depot_ids.append(int(line))


        if depot_ids:
            depot_id = depot_ids[0]
        else:
            depot_candidates = [i for i, d in demands_by_id.items() if d == 0]
            depot_id = depot_candidates[0]

        dim = dimension
        N = dim - 1

        node_ids: List[int] = [depot_id] + sorted(
            i for i in range(1, dim + 1) if i != depot_id
        )
        
        demand: List[int] = []
        for orig_id in node_ids[1:]:
            demand.append(demands_by_id[orig_id])

        N_plus_1 = N + 1
        distance: List[List[int]] = [[0] * N_plus_1 for _ in range(N_plus_1)]

        for i in range(N_plus_1):
            for j in range(N_plus_1):
                if i == j:
                    distance[i][j] = 0
                else:
                    pi = coords[node_ids[i]]
                    pj = coords[node_ids[j]]
                    distance[i][j] = _euc2d(pi, pj)

        return cls(
            N=N,
            Capacity=capacity,
            Demand=demand,
            Distance=distance,
        )


    def to_dict(self) -> dict:
        """
        Directory in format used by MiniZinc Python API.
        """
        return {
            "N": self.N,
            "Capacity": self.Capacity,
            "Demand": list(self.Demand),
            "Distance": [list(row) for row in self.Distance],
        }

    def to_dzn(self) -> str:
        """
        .dzn format used by pure MiniZinc models

            N = ...;
            Capacity = ...;
            Demand = [d1, d2, ..., dN];
            Distance = [|
              row0
            | row1
            | ...
            | rowN
            |];
        """
        N = self.N
        capacity = self.Capacity
        demands = self.Demand
        distance = self.Distance

        lines: List[str] = []

        lines.append(f"N = {N};")
        lines.append(f"Capacity = {capacity};")

        demand_str = ", ".join(str(d) for d in demands)
        lines.append(f"Demand = [{demand_str}];")

        lines.append("Distance = [|")
        for i, row in enumerate(distance):
            row_str = ", ".join(str(x) for x in row)
            prefix = "  " if i == 0 else "| "
            lines.append(f"{prefix}{row_str}")
        lines.append("|];")

        return "\n".join(lines) + "\n"
