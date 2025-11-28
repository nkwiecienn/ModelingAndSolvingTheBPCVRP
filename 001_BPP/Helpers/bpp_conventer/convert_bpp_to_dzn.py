#!/usr/bin/env python3
"""
Convert BPP txt instances into MiniZinc .dzn files.

Expected txt format for each instance:

Line 1: number of items n
Line 2: bin capacity c
Line 3..(n+2): size/weight of each item (one integer per line)

Example:
5
10
2
4
5
7
3
"""

import argparse
from pathlib import Path


def convert_file(txt_path: Path, out_dir: Path):
    # Read all non-empty, non-comment lines
    with txt_path.open() as f:
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    if len(lines) < 2:
        raise ValueError(f"{txt_path}: file too short, need at least n and capacity.")

    try:
        n = int(lines[0])
        capacity = int(lines[1])
    except ValueError as e:
        raise ValueError(f"{txt_path}: first two lines must be integers (n, capacity).") from e

    sizes_raw = lines[2:]
    if len(sizes_raw) < n:
        raise ValueError(
            f"{txt_path}: expected {n} item sizes, but found only {len(sizes_raw)}."
        )

    sizes = []
    for i in range(n):
        try:
            sizes.append(int(sizes_raw[i]))
        except ValueError as e:
            raise ValueError(
                f"{txt_path}: item {i+1} size is not an integer: {sizes_raw[i]!r}"
            ) from e

    # Build MiniZinc .dzn content
    dzn_lines = [
        f"n = {n};",
        f"capacity = {capacity};",
        "size = [" + ", ".join(str(s) for s in sizes) + "];",
    ]
    dzn_text = "\n".join(dzn_lines) + "\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (txt_path.stem + ".dzn")
    out_path.write_text(dzn_text, encoding="utf-8")

    print(f"Converted {txt_path} -> {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert BPP txt instances (n, capacity, item sizes) to MiniZinc .dzn."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Directory containing .txt files in the BPP format.",
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Directory where .dzn files will be written.",
    )

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    if not in_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {in_dir}")

    txt_files = sorted(in_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {in_dir}")
        return

    for txt_file in txt_files:
        try:
            convert_file(txt_file, out_dir)
        except Exception as e:
            print(f"ERROR converting {txt_file}: {e}")


if __name__ == "__main__":
    main()
