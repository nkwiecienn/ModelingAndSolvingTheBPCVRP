from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Union

from ..solvers.minizinc_runner import MiniZincRunner, SolveResult


PathLike = Union[str, Path]


class HasToDict(Protocol):
    def to_dict(self) -> Dict[str, Any]: ...


def _instance_name(instance: Any, index: int) -> str:
    """Try to produce a readable name for an instance:

    - use `.name` if present and non-empty
    - else use the basename of `.filename` or `.path` if available
    - otherwise return a generic `instance_<i>` string
    """
    # 1) .name
    name = getattr(instance, "name", None)
    if isinstance(name, str) and name.strip():
        return name

    # 2) .filename / .path
    for attr in ("filename", "path"):
        p = getattr(instance, attr, None)
        if p is not None:
            try:
                return Path(p).name
            except TypeError:
                pass

    # 3) fallback
    return f"instance_{index}"


def run_batch(
    instances: Iterable[HasToDict],
    model_path: PathLike,
    solver_name: str,
    time_limit: Optional[float] = None,
    print_progress: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run a batch of experiments for the given iterable of instances and a MiniZinc model.

    Parameters
    ----------
    instances: Iterable[HasToDict]
        Objects providing a `.to_dict()` method. Examples: `BPPInstance`, `VRPInstance`, `BPCVRPInstance`.
    model_path: str | Path
        Path to the `.mzn` model file (e.g. 'models/bpp_002.mzn').
    solver_name: str
        MiniZinc solver identifier (e.g. 'chuffed', 'gecode', 'cbc').
    time_limit: float | None
        Time limit in seconds per instance. If None → no time limit.
    print_progress: bool
        Whether to print progress to stdout during the run.

    Returns
    -------
    List[Dict[str, Any]]
        A list of result rows (dicts) for each instance. Example row keys:
        {
            "instance": str,
            "problem_type": str,
            "status": str,
            "has_solution": bool,
            "objective": float | None,
            "time_sec": float,
            "timed_out": bool | None,
            ... (other fields may appear)
        }
    """
    model_path = Path(model_path)
    runner = MiniZincRunner(model_path, solver_name)

    results: List[Dict[str, Any]] = []

    if print_progress:
        print(
            f"\nRunning batch: model={model_path.name}, "
            f"solver={solver_name}, time_limit={time_limit}\n"
        )
        header = (
            f"{'instance':35s}  "
            f"{'status':20s}  "
            f"{'obj':>10s}  "
            f"{'time[s]':>8s}  "
            f"{'timed_out':>9s}"
        )
        print(header)
        print("-" * len(header))

    for idx, inst in enumerate(instances):
        inst_name = _instance_name(inst, idx)
        problem_type = type(inst).__name__

        res: SolveResult = runner.solve_instance(inst, time_limit=time_limit)

        if time_limit is not None:
            timed_out = (not res.has_solution) or (res.time >= time_limit - 1e-3)
        else:
            timed_out = None

        row: Dict[str, Any] = {
            "instance": inst_name,
            "problem_type": problem_type,
            "status": res.status,
            "has_solution": res.has_solution,
            "objective": res.objective,
            "time_sec": round(res.time, 6),
            "timed_out": timed_out,
        }

        results.append(row)

        if print_progress:
            obj_str = "-" if res.objective is None else f"{res.objective:.4g}"
            t_str = f"{res.time:8.3f}"
            to_str = "-" if timed_out is None else str(bool(timed_out))
            print(
                f"{inst_name:35s}  "
                f"{res.status:20s}  "
                f"{obj_str:>10s}  "
                f"{t_str}  "
                f"{to_str:>9s}"
            )

    return results


def save_results_csv(results: List[Dict[str, Any]], path: PathLike) -> None:
    """
    Write a list of result dictionaries to a CSV file.

    The function is intentionally generic:
    - it collects all keys appearing in any row
    - writes them as CSV columns (missing values become empty cells)

    Parameters
    ----------
    results: List[dict]
        Results produced, e.g., by `run_batch()`.
    path: str | Path
        Path to the output CSV file.
    """
    if not results:
        Path(path).write_text("", encoding="utf-8")
        return

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    all_keys: set[str] = set()
    for row in results:
        all_keys.update(row.keys())

    preferred_order = [
        "instance",
        "problem_type",
        "status",
        "has_solution",
        "objective",
        "time_sec",
        "timed_out",
    ]
    remaining_keys = sorted(k for k in all_keys if k not in preferred_order)
    fieldnames = preferred_order + remaining_keys

    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
