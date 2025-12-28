from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import time
import datetime as dt

import minizinc


PathLike = Union[str, Path]


@dataclass
class SolveResult:
    """Unified result of running a MiniZinc model.

    Fields:
    - status: string name of the result status (e.g. "OPTIMAL_SOLUTION", "UNSATISFIABLE", "UNKNOWN")
    - has_solution: whether a solution object is present
    - objective: objective value as float, or None for SAT models or missing value
    - solution: output variables as a dict (if available)
    - time: elapsed time in seconds (float)
    - raw_result: original `minizinc.Result` object for advanced inspection
    """
    status: str
    has_solution: bool
    objective: Optional[float]
    solution: Optional[Dict[str, Any]]
    time: float
    raw_result: Any


class MiniZincRunner:
    """Generic wrapper to run MiniZinc models from Python.

    Usage example:
    >>> runner = MiniZincRunner("models/bpp_002.mzn", solver_name="chuffed")
    >>> data = {"n": 10, "capacity": 50, "size": [5, 7, ...]}
    >>> res = runner.solve(data, time_limit=60)
    >>> print(res.status, res.objective, res.time)
    """

    def __init__(self, model_path: PathLike, solver_name: str = "chuffed"):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        self.model = minizinc.Model(str(self.model_path))
        self.solver = minizinc.Solver.lookup(solver_name)


    def solve(
        self,
        data: Dict[str, Any],
        time_limit: Optional[float] = None,
        all_solutions: bool = False,
        free_search: bool = False,
        threads: Optional[int] = None,
        **kwargs: Any,
    ) -> SolveResult:
        """Run the model for the given input data.

        Parameters
        ----------
        data: dict
            Input data (MiniZinc parameters), e.g.:
            {"n": 10, "capacity": 50, "size": [5,7,...]} for BPP
            {"N": 20, "Capacity": 100, "Demand": [...], "Distance": [[...], ...]} for VRP
        time_limit: float | None
            Time limit in seconds (optional). If None, no limit is set.
        all_solutions: bool
            Whether to request all solutions (mainly for SAT-like models).
        free_search: bool
            Allow the solver to ignore the model's search strategy.
        **kwargs:
            Additional keyword arguments passed to `Instance.solve()`.

        Returns
        -------
        SolveResult
            Contains status, has_solution flag, objective value, solution dict and elapsed time.
        """
        inst = minizinc.Instance(self.solver, self.model)

        for name, value in data.items():
            inst[name] = value

        tl: Optional[dt.timedelta] = None
        if time_limit is not None:
            tl = dt.timedelta(seconds=float(time_limit))

        if threads is not None:
            kwargs["processes"] = int(threads)

        start = time.perf_counter()
        result = inst.solve(
            time_limit=tl,
            all_solutions=all_solutions,
            free_search=free_search,
            **kwargs,
        )
        end = time.perf_counter()

        elapsed = end - start

        status_str = getattr(result.status, "name", str(result.status))

        sol_obj = None
        if result.solution is not None:
            if isinstance(result.solution, list):
                # take the last (usually best) solution
                sol_obj = result.solution[-1]
            else:
                sol_obj = result.solution

        has_solution = sol_obj is not None

        objective: Optional[float] = None
        if has_solution:
            if hasattr(sol_obj, "objective"):
                objective = float(getattr(sol_obj, "objective"))
            else:
                try:
                    obj_val = result["objective"]
                    if obj_val is not None:
                        objective = float(obj_val)
                except Exception:
                    objective = None

        sol_dict: Optional[Dict[str, Any]] = None
        if has_solution:
            raw = vars(sol_obj)
            sol_dict = {
                k: v for k, v in raw.items()
                if not k.startswith("_") and k not in {"__output_item"}
            }

        return SolveResult(
            status=status_str,
            has_solution=has_solution,
            objective=objective,
            solution=sol_dict,
            time=elapsed,
            raw_result=result,
        )

    def solve_instance(
        self,
        instance_obj: Any,
        time_limit: Optional[float] = None,
        all_solutions: bool = False,
        free_search: bool = False,
        **kwargs: Any,
    ) -> SolveResult:
        """Convenience wrapper: accepts an object with a `.to_dict()` method

        Examples: `BPPInstance`, `VRPInstance`
        """
        if not hasattr(instance_obj, "to_dict"):
            raise TypeError("`instance_obj` must implement a `.to_dict()` method")

        data = instance_obj.to_dict()
        return self.solve(
            data,
            time_limit=time_limit,
            all_solutions=all_solutions,
            free_search=free_search,
            **kwargs,
        )