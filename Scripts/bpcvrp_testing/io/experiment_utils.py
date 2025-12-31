from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import matplotlib.pyplot as plt


# ----------------------------------------------------------------------
# Project palette
# ----------------------------------------------------------------------

THESIS_COLORS = {
    "primary": "#1F4E79",   # line
    "accent":  "#D99C2B",   # optimal points
    "muted":   "#E6E6E6",   # grid
    "bad":     "#B34E4E",   # non-optimal points
    "text":    "#1A1A1A",
}


def is_optimal(status: str | None) -> bool:
    """Treat any status containing 'OPTIMAL' as optimal."""
    return bool(status) and ("OPTIMAL" in str(status).upper())


# ----------------------------------------------------------------------
# Saving results
# ----------------------------------------------------------------------

def result_to_dict(instance_path: Path, res: Any) -> dict[str, Any]:
    """
    Convert a solve result to a JSON-serialisable dict.

    Designed to work with your MiniZincRunner SolveResult object
    (status/has_solution/objective/time/solution/raw_result).
    """
    return {
        "instance_path": str(instance_path),
        "status": getattr(res, "status", None),
        "has_solution": getattr(res, "has_solution", None),
        "objective": getattr(res, "objective", None),
        "time": getattr(res, "time", None),
        "solution": getattr(res, "solution", None),
        "raw_result": str(getattr(res, "raw_result", "")),
    }


def save_result_json(instance_path: Path, res: Any, out_path: Path) -> None:
    payload = result_to_dict(instance_path, res)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------
# Printing
# ----------------------------------------------------------------------

def print_solve_header(title: str) -> None:
    print("\n" + title)
    print("=" * 50)


def print_instance(instance: Any) -> None:
    """Print instance nicely without hardcoding types."""
    if hasattr(instance, "to_string"):
        print(instance.to_string())
        return
    if is_dataclass(instance):
        print(asdict(instance))
        return
    print(str(instance))


def print_solve_result(res: Any, *, extra_lines: Optional[Sequence[str]] = None) -> None:
    print(f"Status     : {getattr(res, 'status', None)}")
    print(f"Objective  : {getattr(res, 'objective', None)}")
    t = getattr(res, "time", None)
    if t is not None:
        try:
            print(f"Time [s]   : {float(t):.2f}")
        except Exception:
            print(f"Time [s]   : {t}")
    else:
        print("Time [s]   : (unknown)")
    if extra_lines:
        for line in extra_lines:
            print(line)


# ----------------------------------------------------------------------
# Plotting
# ----------------------------------------------------------------------

def plot_runtime_vs_size(
    results: Sequence[Mapping[str, Any]],
    *,
    x_key: str,
    y_key: str = "time",
    optimal_key: str = "optimal",
    group_key: str | None = None,
    title: str = "Runtime vs size",
    xlabel: str = "size",
    ylabel: str = "Time [s]",
    out_path: Path | None = None,
) -> None:
    """
    One plotting function for BPP/VRP/BPCVRP etc.

    - If `group_key` is None: one plot.
    - If `group_key` is provided: one plot per group value.

    Each row should contain: x_key, y_key, optimal_key.
    """

    if not results:
        return

    def _plot_one(subset: Sequence[Mapping[str, Any]], plot_title: str, save_to: Path | None) -> None:
        xs = [int(r[x_key]) for r in subset]
        ys = [float(r[y_key]) for r in subset]
        oks = [bool(r.get(optimal_key, False)) for r in subset]

        fig, ax = plt.subplots(figsize=(7.5, 4.5))

        ax.plot(xs, ys, color=THESIS_COLORS["primary"], linewidth=2, marker="o", markersize=5, label="Time")

        opt_x = [x for x, ok in zip(xs, oks) if ok]
        opt_y = [y for y, ok in zip(ys, oks) if ok]
        non_x = [x for x, ok in zip(xs, oks) if not ok]
        non_y = [y for y, ok in zip(ys, oks) if not ok]

        if opt_x:
            ax.scatter(
                opt_x, opt_y,
                color=THESIS_COLORS["accent"],
                edgecolor=THESIS_COLORS["text"],
                s=60, label="Optimal", zorder=3
            )
        if non_x:
            ax.scatter(
                non_x, non_y,
                color=THESIS_COLORS["bad"],
                marker="X",
                s=70, label="Not optimal", zorder=3
            )

        ax.set_title(plot_title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=THESIS_COLORS["muted"], linestyle="--", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(frameon=False)

        fig.tight_layout()
        if save_to is not None:
            save_to.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_to, dpi=200)
            print(f"Saved plot: {save_to}")
        else:
            plt.show()
        plt.close(fig)

    if group_key is None:
        _plot_one(results, title, out_path)
        return

    # group plots
    groups: dict[Any, list[Mapping[str, Any]]] = {}
    for r in results:
        g = r.get(group_key)
        groups.setdefault(g, []).append(r)

    for g, subset in groups.items():
        save_to = None
        if out_path is not None:
            out_dir = out_path if out_path.suffix == "" else out_path.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            save_to = out_dir / f"{group_key}_{g}_{x_key}_vs_{y_key}.png"

        _plot_one(subset, f"{title} ({group_key}={g})", save_to)
