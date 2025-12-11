from dataclasses import dataclass
import time
from typing import Any, Dict, Optional
from bpcvrp_testing.instances.bpp_instance import BPPInstance
from ortools.linear_solver import pywraplp


@dataclass
class SolveResult:
    status: str
    has_solution: bool
    objective: Optional[float]
    solution: Optional[Dict[str, Any]]
    time: float
    raw_result: Any


class ORToolsBPPRunner:
    def __init__(self, solver_name: str = "SCIP"):
        self.solver_name = solver_name

    def solve(self, data: Dict[str, Any], time_limit: Optional[float] = None) -> SolveResult:
        solver = pywraplp.Solver.CreateSolver(self.solver_name)

        if not solver:
            return
        
        # Variables
        # x[i, j] = 1 if item i is packed in bin j.
        x = {}
        for i in range(data["items"]):
            for j in range(data["bins"]):
                x[(i, j)] = solver.IntVar(0, 1, "x_%i_%i" % (i, j))

        # y[j] = 1 if bin j is used.
        y = {}
        for j in range(data["bins"]):
            y[j] = solver.IntVar(0, 1, "y[%i]" % j)

        # Constraints
        # Each item must be in exactly one bin.
        for i in range(data["items"]):
            solver.Add(sum(x[i, j] for j in range(data["bins"])) == 1)

        # The amount packed in each bin cannot exceed its capacity.
        for j in range(data["bins"]):
            solver.Add(
                sum(x[(i, j)] * data["weights"][i] for i in range(data["items"]))
                <= y[j] * data["bin_capacity"]
            )

        # Objective: minimize the number of bins used.
        solver.Minimize(solver.Sum([y[j] for j in range(data["bins"])]))

        if time_limit is not None:
            solver.SetTimeLimit(int(1000 * time_limit))

        status_code = solver.Solve()
        status_str = self._decode_status(status_code)
        has_solution = status_code == pywraplp.Solver.OPTIMAL or status_code == pywraplp.Solver.FEASIBLE

        objective = solver.Objective().Value() if has_solution else None
        solution_dict = {}

        if has_solution:
            solution_dict["bin_items"] = {
                j: [i for i in range(data["items"]) if x[i, j].solution_value() > 0.5]
                for j in range(data["bins"]) if y[j].solution_value() > 0.5
            }

        return SolveResult(
            status=status_str,
            has_solution=has_solution,
            objective=objective,
            solution=solution_dict,
            time=solver.WallTime() / 1000,
            raw_result=solver,
        )
    
    def solve_instance(self, instance_obj: BPPInstance, time_limit: Optional[float] = None) -> SolveResult:
        return self.solve(instance_obj.to_ortools(), time_limit=time_limit)
    
    def _decode_status(self, code: int) -> str:
        status_map = {
            pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE",
            pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
            pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
            pywraplp.Solver.ABNORMAL: "ABNORMAL",
            pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
        }
        return status_map.get(code, f"UNKNOWN({code})")
        