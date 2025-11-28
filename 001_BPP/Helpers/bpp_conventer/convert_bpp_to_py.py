from pathlib import Path


def load_bpp_instance(txt_path):
    """
    Load a BPP instance from a txt file with format:

    Line 1: number of items n
    Line 2: bin capacity c
    Lines 3..(n+2): item weights w_j, one per line

    Returns a dict suitable for MiniZinc Python API:
        {
            "n": n,
            "capacity": capacity,
            "size": [w1, w2, ..., wn]
        }
    """
    txt_path = Path(txt_path)

    with txt_path.open() as f:
        # strip empty lines and comments if any
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    if len(lines) < 2:
        raise ValueError(f"{txt_path}: need at least two lines (n and capacity)")

    try:
        n = int(lines[0])
        capacity = int(lines[1])
    except ValueError as e:
        raise ValueError(
            f"{txt_path}: first two lines must be integers (n, capacity)"
        ) from e

    sizes_raw = lines[2:]
    if len(sizes_raw) < n:
        raise ValueError(
            f"{txt_path}: expected {n} item sizes, found only {len(sizes_raw)}"
        )

    sizes = []
    for i in range(n):
        try:
            sizes.append(int(sizes_raw[i]))
        except ValueError as e:
            raise ValueError(
                f"{txt_path}: item {i+1} size is not an integer: {sizes_raw[i]!r}"
            ) from e

    return {
        "n": n,
        "capacity": capacity,
        "size": sizes,
    }
