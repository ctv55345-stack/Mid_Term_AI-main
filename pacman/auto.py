from __future__ import annotations

import sys
import os

# thêm thư mục cha (project) vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from puzzle import AStar

from pacman.environment import PacmanEnvironment, PacmanProblem
from pacman.heuristics import (
    FoodMSTHeuristic,
    PieAwareHeuristic,
    ExactDistanceHeuristic,
    ExactMSTHeuristic,
    CombinedHeuristic,
)


def _select_heuristic(name: str, environment: PacmanEnvironment):
    name = name.lower()

    if name in {"auto", "dynamic"}:
        return _select_auto(environment)

    mapping = {
        "pie": PieAwareHeuristic,
        "pie-aware": PieAwareHeuristic,
        "adaptive": PieAwareHeuristic,
        "mst": FoodMSTHeuristic,
        "food-mst": FoodMSTHeuristic,
        "exact": ExactMSTHeuristic,
        "exact-mst": ExactMSTHeuristic,
        "shortest": ExactMSTHeuristic,
        "h1": ExactMSTHeuristic,
        "exact-dist": ExactDistanceHeuristic,
        "distance": ExactDistanceHeuristic,
        "combo": CombinedHeuristic,
        "combined": CombinedHeuristic,
        "max": CombinedHeuristic,
    }
    cls = mapping.get(name)
    if cls is None:
        raise ValueError(f"Heuristic '{name}' không được hỗ trợ.")
    return cls(environment)


def _select_auto(environment: PacmanEnvironment):
    """Chọn heuristic dựa trên độ phức tạp layout."""
    layout = environment.layouts[0]
    open_cells = layout.width * layout.height - len(layout.walls)
    food_count = len(layout.food)
    pie_count = len(layout.pies)
    ghost_count = len(layout.ghost_starts)

    # Tiêu chí đơn giản:
    # - Layout rộng hoặc có nhiều food/ghost -> dùng Combined 
    # - Layout nhỏ/vừa -> ExactMST đủ nhanh và nhẹ.
    if (
        open_cells > 200
        or food_count >= 12
        or ghost_count > 1
        or pie_count > 1
    ):
        return CombinedHeuristic(environment)
    return ExactMSTHeuristic(environment)


def run_auto_mode(layout_lines, heuristic: str = "auto"):
    """Chạy chế độ tự động: trả về (path, cost, expanded, frontier_max)."""
    environment = PacmanEnvironment(layout_lines)
    problem = PacmanProblem(environment)
    heuristic_obj = _select_heuristic(heuristic, environment)
    solver = AStar(problem, heuristic_obj)
    return solver.search()


__all__ = ["run_auto_mode"]
