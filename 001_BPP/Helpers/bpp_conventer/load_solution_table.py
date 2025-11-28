import re
from pathlib import Path

import pandas as pd


# ---------- Helpers to read Solutions.xlsx ----------

def normalize_instance_key(name: str) -> str:
    """Return a canonical key for instance names so variants still match."""
    if not name:
        return ""

    key = str(name).strip()
    key = key.replace("\\", "/").split("/")[-1]  # drop directories
    key = key.lower()
    if key.endswith(".txt"):
        key = key[:-4]

    # Compress whitespace/hyphen sequences to underscores for consistency
    key = re.sub(r"[\s-]+", "_", key)

    # Remove leading zeros from each number block (Falkenauer_u0120 -> Falkenauer_u120)
    key = re.sub(r"\d+", lambda m: str(int(m.group())), key)
    return key

def load_solution_table(xlsx_path: Path, sheet_name: str):
    """
    Load one sheet from Solutions.xlsx.

    Expected columns (per BPPLIB README :contentReference[oaicite:1]{index=1}):
    - Name of the instance
    - Best LB
    - Best UB
    - Status
    - Comment
    (we ignore others)
    """
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

    # Normalize column names a bit
    cols = {c.lower().strip(): c for c in df.columns}

    def pick_column(*candidates):
        """
        Return the first matching column header.

        Some sheets use 'Name', others 'Name of the instance', etc.  We first try
        an exact normalized match, then fall back to substring containment.
        """
        for cand in candidates:
            cand_norm = cand.lower().strip()
            if cand_norm in cols:
                return cols[cand_norm]
        for key, original in cols.items():
            for cand in candidates:
                cand_norm = cand.lower().strip()
                if cand_norm and cand_norm in key:
                    return original
        return None

    name_col = pick_column("Name", "Name of the instance")
    lb_col = pick_column("Best LB", "LB")
    ub_col = pick_column("Best UB", "UB")
    status_col = pick_column("Status")
    comment_col = pick_column("Comment")

    if name_col is None or lb_col is None or ub_col is None:
        raise ValueError(
            f"Sheet {sheet_name} must contain at least "
            f"'Name of the instance', 'Best LB', 'Best UB' columns."
        )

    sol_map = {}
    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name:
            continue
        lb = row[lb_col]
        ub = row[ub_col]
        status = row[status_col] if status_col is not None else None
        comment = row[comment_col] if comment_col is not None else None

        # Sometimes LB/UB may be floats; store as numbers or None
        try:
            lb_val = int(lb) if pd.notna(lb) else None
        except Exception:
            lb_val = None
        try:
            ub_val = int(ub) if pd.notna(ub) else None
        except Exception:
            ub_val = None

        # Comment: expected optimal value for some open instances
        try:
            comment_val = int(comment) if pd.notna(comment) else None
        except Exception:
            comment_val = None

        key = normalize_instance_key(name)
        if not key:
            continue

        sol_map[key] = {
            "lb": lb_val,
            "ub": ub_val,
            "status": str(status) if status is not None else None,
            "comment_opt": comment_val,
        }

    return sol_map


def lookup_solution_info(sol_map, file_path: Path):
    """
    Try to match a txt instance file to a row in Solutions.xlsx.

    We try several keys:
    - full file name, e.g. 'BPP_20_5_10_100_0.txt'
    - stem only, e.g. 'BPP_20_5_10_100_0'
    - stem + '.txt' if needed
    """
    fname = file_path.name
    stem = file_path.stem

    candidates = [fname, stem, stem + ".txt"]
    for key in candidates:
        norm_key = normalize_instance_key(key)
        if norm_key in sol_map:
            return sol_map[norm_key]

    # Not found
    return {"lb": None, "ub": None, "status": None, "comment_opt": None}
