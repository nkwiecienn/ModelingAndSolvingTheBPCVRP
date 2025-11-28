#!/usr/bin/env python3
import argparse
from pathlib import Path
from load_solution_table import load_solution_table, lookup_solution_info
from minizinc_runner import run_bpp_txt_instance

def main():
    parser = argparse.ArgumentParser(
        description="Run BPP experiments for a given MiniZinc model + solver and compare to Solutions.xlsx."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Directory containing BPP .txt instance files.",
    )
    parser.add_argument(
        "model_path",
        type=str,
        help="Path to MiniZinc model (.mzn).",
    )
    parser.add_argument(
        "solver_id",
        type=str,
        help="MiniZinc solver id (e.g. chuffed, gecode, mip, cp-sat).",
    )
    parser.add_argument(
        "solutions_xlsx",
        type=str,
        help="Path to Solutions.xlsx file (BPPLIB).",
    )
    parser.add_argument(
        "sheet_name",
        type=str,
        help="Name of sheet in Solutions.xlsx corresponding to these instances.",
    )
    parser.add_argument(
        "--time_limit",
        type=float,
        default=60.0,
        help="Time limit per instance in seconds (default: 60).",
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default="experiment_results.csv",
        help="Output CSV file (default: experiment_results.csv).",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    model_path = Path(args.model_path)
    solver_id = args.solver_id
    solutions_xlsx = Path(args.solutions_xlsx)
    sheet_name = args.sheet_name
    time_limit_sec = args.time_limit
    output_csv = Path(args.output_csv)

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")
    if not model_path.is_file():
        raise SystemExit(f"Model file does not exist: {model_path}")
    if not solutions_xlsx.is_file():
        raise SystemExit(f"Solutions file does not exist: {solutions_xlsx}")

    print(f"Loading solution table from {solutions_xlsx} [sheet={sheet_name}]...")
    sol_map = load_solution_table(solutions_xlsx, sheet_name)

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    rows = []

    print(
        f"\nRunning experiments: model={model_path.name}, solver={solver_id}, "
        f"time_limit={time_limit_sec}s\n"
    )
    print(
        f"{'instance':35s}  {'LB':>6}  {'UB':>6}  {'gap':>6}  "
        f"{'found':>6}  {'ok?':>4}  {'time[s]':>8}  {'timed_out':>9}"
    )
    print("-" * 90)

    max_consecutive_timeouts = 5
    consecutive_timeouts = 0

    for txt_path in txt_files:
        sol_info = lookup_solution_info(sol_map, txt_path)
        lb = sol_info["lb"]
        ub = sol_info["ub"]
        status_ref = sol_info["status"]
        comment_opt = sol_info["comment_opt"]

        result, elapsed = run_bpp_txt_instance(
            txt_path, model_path, solver_id, time_limit_sec
        )

        objective = None
        status = None
        has_solution = False

        if result is not None:
            status = result.status
            has_solution = status.has_solution()
            if has_solution and hasattr(result, "objective"):
                objective = result.objective

        gap = None
        if lb is not None and ub is not None:
            gap = ub - lb

        known_opt = None
        if lb is not None and ub is not None and lb == ub:
            known_opt = ub
        elif comment_opt is not None:
            known_opt = comment_opt

        correct = None
        if known_opt is not None and objective is not None:
            correct = (objective == known_opt)

        timed_out = (not has_solution) or (elapsed >= time_limit_sec - 1e-3)

        rows.append(
            {
                "instance": txt_path.name,
                "lb": lb,
                "ub": ub,
                "gap": gap,
                "status_ref": status_ref,
                "known_opt": known_opt,
                "found_obj": objective,
                "correct": correct,
                "time_sec": round(elapsed, 4),
                "timed_out": timed_out,
            }
        )

        lb_str = f"{lb}" if lb is not None else "-"
        ub_str = f"{ub}" if ub is not None else "-"
        gap_str = f"{gap}" if gap is not None else "-"
        found_str = f"{objective}" if objective is not None else "-"
        ok_str = "?" if correct is None else ("yes" if correct else "no")

        print(
            f"{txt_path.name:35s}  {lb_str:>6}  {ub_str:>6}  {gap_str:>6}  "
            f"{found_str:>6}  {ok_str:>4}  {elapsed:8.3f}  {str(timed_out):>9}"
        )

        # Stop if we reach too many consecutive timeouts
        # if timed_out:
        #     consecutive_timeouts += 1
        #     if consecutive_timeouts >= max_consecutive_timeouts:
        #         print(
        #             f"\nReached {max_consecutive_timeouts} consecutive time-limit hits "
        #             f"({time_limit_sec}s) – stopping further instances."
        #         )
        #         break
        # else:
        #     consecutive_timeouts = 0


    # Write CSV
    import csv
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "instance",
                "lb",
                "ub",
                "gap",
                "status_ref",
                "known_opt",
                "found_obj",
                "correct",
                "time_sec",
                "timed_out",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {output_csv.resolve()}")


if __name__ == "__main__":
    main()
