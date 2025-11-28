# minizinc_runner.py
import time
import datetime
from pathlib import Path

import minizinc
from convert_bpp_to_py import load_bpp_instance


def run_bpp_txt_instance(
    txt_path,
    model_path,
    solver_id="chuffed",
    time_limit_sec=60,
):
    """
    Run a BPP txt instance with a given MiniZinc model and solver.

    Parameters
    ----------
    txt_path : str or Path
        Path to the .txt file (n, capacity, item sizes).
    model_path : str or Path
        Path to the MiniZinc model (.mzn).
    solver_id : str
        MiniZinc solver id, e.g. "chuffed", "gecode", "mip", ...
    time_limit_sec : int or float
        Time limit in seconds.

    Returns
    -------
    (result, elapsed_seconds)
        result : minizinc.Result
        elapsed_seconds : float
    """
    txt_path = Path(txt_path)
    model_path = Path(model_path)

    # 1. Load data from txt into Python dict
    data = load_bpp_instance(txt_path)

    # 2. Prepare MiniZinc model + instance
    model = minizinc.Model(model_path.as_posix())
    solver = minizinc.Solver.lookup(solver_id)
    instance = minizinc.Instance(solver, model)

    # 3. Push parameters to MiniZinc
    instance["n"] = data["n"]
    instance["capacity"] = data["capacity"]
    instance["size"] = data["size"]

    # 4. Solve with time limit
    start = time.perf_counter()
    try:
        result = instance.solve(
            time_limit=datetime.timedelta(seconds=time_limit_sec)
        )
        elapsed = time.perf_counter() - start

        # 5. Print some info to console
        print(f"File:   {txt_path}")
        print(f"Model:  {model_path.name}")
        print(f"Solver: {solver_id}")
        print(f"Status: {result.status}")
        # Try to print objective if present
        if hasattr(result, "objective"):
            print(f"Objective: {result.objective}")
        print(f"Time:   {elapsed:.3f} s")
        print("-" * 40)

        return result, elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"[ERROR] Running {model_path.name} on {txt_path} with {solver_id}: {e}")
        print(f"Elapsed (until error): {elapsed:.3f} s")
        print("-" * 40)
        return None, elapsed
