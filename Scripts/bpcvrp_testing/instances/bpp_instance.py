from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class BPPInstance:
    n: int
    capacity: int
    sizes: List[int]

    @classmethod
    def from_txt(cls, path: str | Path) -> "BPPInstance":
        """
        Based on instances from https://github.com/mdelorme2/BPPLIB I assume the txt format to be:

        Line 1: number if items
        Line 2: bin capacity
        Lines 3..(n+2): weight of items (one item per line)
        """
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")

        # Ignore empty lines
        raw_lines = p.read_text(encoding="utf-8").splitlines()
        lines: List[str] = []
        for ln in raw_lines:
            stripped = ln.strip()
            if not stripped:
                continue
            lines.append(stripped)

        n = int(lines[0])
        capacity = int(lines[1])
        sizes = [int(x) for x in lines[2:]]

        return cls(n=n, capacity=capacity, sizes=sizes)

    def to_dict(self) -> Dict[str, Any]:
        """
        Directory in format used by MiniZinc Python API.
        """
        return {
            "n": self.n,
            "capacity": self.capacity,
            "size": list(self.sizes),
        }
    
    def to_ortools(self) -> Dict[str, Any]:
        """
        Dictionary in format used by OR-Tools CP-SAT solver.
        """
        return {
            "weights": list(self.sizes),
            "items": self.n,
            "bins": self.n,
            "bin_capacity": self.capacity
        }

    def to_dzn(self) -> str:
        """
        .dzn format used by pure MiniZinc models

        n = 5;
        capacity = 10;
        size = [2, 4, 5, ...];
        """
        sizes_str = ", ".join(str(s) for s in self.sizes)
        return (
            f"n = {self.n};\n"
            f"capacity = {self.capacity};\n"
            f"size = [{sizes_str}];\n"
        )
