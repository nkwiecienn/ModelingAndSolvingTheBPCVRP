from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Union

from ..solvers.minizinc_runner import MiniZincRunner, SolveResult

PathLike = Union[str, Path]


class HasToDict(Protocol):
    def to_dict(self) -> Dict[str, Any]: ...


def _instance_name(instance: Any, index: int) -> str:
    """Try to produce a readable name for an instance.

    Priority:
    1) use `.name` if present and non-empty
    2) else use the basename of `.filename` or `.path` if available
    3) otherwise return `instance_<i>`
    """
    name = getattr(instance, "name", None)
    if isinstance(name, str) and name.strip():
        return name

    for attr in ("filename", "path"):
        p = getattr(instance, attr, None)
        if p is not None:
            try:
                return Path(p).name
            except TypeError:
                pass

    return f"instance_{index}"


def run_batch(
    instances: Iterable[HasToDict],
    model_path: PathLike,
    solver_name: str,
    time_limit: Optional[float] = None,
    threads: Optional[int] = None,
    print_progress: bool = True,
    extra_metrics_fn: Optional[Callable[[HasToDict, SolveResult], Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Run a batch of experiments for the given iterable of instances and a MiniZinc model.

    Parameters
    ----------
    instances:
        Objects providing a `.to_dict()` method.
    model_path:
        Path to the `.mzn` model file.
    solver_name:
        MiniZinc solver identifier (e.g. 'chuffed', 'gecode', 'cbc').
    time_limit:
        Time limit in seconds per instance. If None -> no time limit.
    print_progress:
        Whether to print progress to stdout.
    extra_metrics_fn:
        Optional callback that extracts additional metrics from (instance, solve_result).
        Returned dict is merged into the CSV row.

    Returns
    -------
    List[Dict[str, Any]]
        A list of per-instance result rows.
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

        res: SolveResult = runner.solve_instance(inst, time_limit=time_limit, threads=threads)

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

        if extra_metrics_fn is not None:
            try:
                extra = extra_metrics_fn(inst, res)
                if isinstance(extra, dict):
                    row.update(extra)
            except Exception as e:
                row["extra_metrics_error"] = str(e)

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

    - collects all keys appearing in any row
    - writes them as CSV columns (missing values become empty cells)
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
