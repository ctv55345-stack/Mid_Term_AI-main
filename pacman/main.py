"""CLI entry point for Pacman Task 2.1 automatic mode."""

from __future__ import annotations

import argparse
from pathlib import Path

from auto import run_auto_mode


DEFAULT_LAYOUT = [
    "%%%%%%%%%%",
    "%P....  E%",
    "% %% %%% %",
    "%..G  O  %",
    "%%%%%%%%%%",
]


def _read_layout(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return [line.rstrip("\n") for line in file]


def main() -> None:
    parser = argparse.ArgumentParser(description="Pacman")
    parser.add_argument(
        "--layout",
        type=Path,
        help="Đường dẫn tới file layout; nếu bỏ trống dùng layout mặc định nhỏ.",
    )
    parser.add_argument(
        "--heuristic",
        default="auto",
        choices=[
            "auto",
            "dynamic",
            "exact",
            "shortest",
            "h1",
            "exact-mst",
            "exact-dist",
            "distance",
            "pie",
            "pie-aware",
            "adaptive",
            "mst",
            "food-mst",
            "combo",
            "combined",
            "max",
        ],
        help="Chọn heuristic. 'auto' (mặc định) tự nhận diện layout; các lựa chọn khác dùng trực tiếp heuristic chỉ định.",
    )
    args = parser.parse_args()

    layout_lines = (
        _read_layout(args.layout)
        if args.layout is not None
        else DEFAULT_LAYOUT
    )

    path, cost, expanded, frontier = run_auto_mode(layout_lines, heuristic=args.heuristic)
    print("Auto mode path:", [str(a) for a in path])
    print(f"Cost: {cost}  Expanded: {expanded}  Max frontier: {frontier}")


if __name__ == "__main__":
    main()
