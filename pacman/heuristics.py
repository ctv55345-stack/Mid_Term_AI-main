from __future__ import annotations

import heapq
from collections import deque
from typing import Deque, Dict, Iterable, List, Tuple

from puzzle import Heuristic

from pacman.environment import PacmanEnvironment, PacmanLayout, PacmanState, Point


def _manhattan(a: Point, b: Point) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(layout: PacmanLayout, pos: Point) -> List[Point]:
    r, c = pos
    moves = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    valid = [p for p in moves if layout.in_bounds(p) and not layout.is_wall(p)]

    corner = layout.corner_name(pos)
    if corner:
        for name, target in layout.teleports.items():
            if target != pos and not layout.is_wall(target):
                valid.append(target)
    return valid


class PieAwareHeuristic(Heuristic):
    PIE_BENEFIT_CAP = 0.2

    def __init__(self, environment: PacmanEnvironment):
        self.env = environment
        self._distance_cache: Dict[Tuple[int, Point, Point], int] = {}

    def _distance(self, layout_index: int, start: Point, goal: Point) -> int:
        key = (layout_index, start, goal)
        if key in self._distance_cache:
            return self._distance_cache[key]

        layout = self.env.layouts[layout_index]
        base = _manhattan(start, goal)
        corners = list(layout.teleports.values())
        best = base
        for c_from in corners:
            dist_to_corner = _manhattan(start, c_from)
            for c_to in corners:
                teleport_dist = dist_to_corner + 1 + _manhattan(c_to, goal)
                if teleport_dist < best:
                    best = teleport_dist

        self._distance_cache[key] = best
        return best

    def calculate(self, state: PacmanState) -> int:
        layout = self.env.layouts[state.layout_index]
        if not state.food:
            return self._distance(state.layout_index, state.pacman_pos, layout.exit_gate)

        min_food = min(
            self._distance(state.layout_index, state.pacman_pos, food_pos)
            for food_pos in state.food
        )

        if state.pie_timer > 0:
            min_food *= 0.5

        pie_benefit = 0.0
        if state.pies:
            min_pie = min(
                self._distance(state.layout_index, state.pacman_pos, pie_pos)
                for pie_pos in state.pies
            )
            pie_benefit = 3.0 / (min_pie + 1.0)

        factor = 1.0 - min(pie_benefit, self.PIE_BENEFIT_CAP)
        return int(min_food * factor)


class FoodMSTHeuristic(Heuristic):
    """Heuristic MST với BFS bỏ tường (giữ để tham chiếu)."""

    def __init__(self, environment: PacmanEnvironment):
        self.env = environment
        self._bfs_cache: Dict[Tuple[int, Point], Dict[Point, int]] = {}

    def calculate(self, state: PacmanState) -> int:
        layout_index = state.layout_index
        layout = self.env.layouts[layout_index]
        if not state.food:
            return self._lower_bound_distance(layout_index, layout, state.pacman_pos, layout.exit_gate)

        targets = list(state.food) + [layout.exit_gate]
        points = [state.pacman_pos] + targets
        pairwise = self._pairwise_lower_bounds(layout_index, layout, points)
        return self._mst_cost(points, pairwise)

    def _pairwise_lower_bounds(
        self,
        layout_index: int,
        layout: PacmanLayout,
        points: List[Point],
    ) -> Dict[Tuple[Point, Point], int]:
        bounds: Dict[Tuple[Point, Point], int] = {}
        for i, src in enumerate(points):
            distances = self._bfs_ignoring_walls(layout_index, layout, src)
            for j in range(i + 1, len(points)):
                dst = points[j]
                bounds[(src, dst)] = bounds[(dst, src)] = distances.get(dst, 0)
        return bounds

    def _mst_cost(
        self,
        points: List[Point],
        distances: Dict[Tuple[Point, Point], int],
    ) -> int:
        if len(points) <= 1:
            return 0

        visited = {points[0]}
        edges = [
            (distances[(points[0], other)], points[0], other)
            for other in points[1:]
        ]
        heapq.heapify(edges)
        total = 0

        while edges and len(visited) < len(points):
            weight, _, node = heapq.heappop(edges)
            if node in visited:
                continue
            visited.add(node)
            total += weight
            for other in points:
                if other not in visited:
                    heapq.heappush(edges, (distances[(node, other)], node, other))

        return total

    def _lower_bound_distance(self, layout_index: int, layout: PacmanLayout, start: Point, goal: Point) -> int:
        return self._bfs_ignoring_walls(layout_index, layout, start).get(goal, 0)

    def _bfs_ignoring_walls(self, layout_index: int, layout: PacmanLayout, start: Point) -> Dict[Point, int]:
        key = (layout_index, start)
        if key in self._bfs_cache:
            return self._bfs_cache[key]

        queue: deque[Tuple[Point, int]] = deque([(start, 0)])
        visited = {start}
        distances = {start: 0}

        while queue:
            pos, dist = queue.popleft()
            row, col = pos
            for delta in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbour = (row + delta[0], col + delta[1])
                if not layout.in_bounds(neighbour) or neighbour in visited:
                    continue
                visited.add(neighbour)
                distances[neighbour] = dist + 1
                queue.append((neighbour, dist + 1))

            corner = layout.corner_name(pos)
            if corner:
                for _, corner_pos in layout.teleports.items():
                    if corner_pos not in visited:
                        visited.add(corner_pos)
                        distances[corner_pos] = dist + 1
                        queue.append((corner_pos, dist + 1))

        self._bfs_cache[key] = distances
        return distances


class ExactDistanceHeuristic(Heuristic):
    """Heuristic dùng khoảng cách ngắn nhất thực tế (có teleport) và MST."""

    def __init__(self, environment: PacmanEnvironment):
        self.env = environment
        self.distance_maps: List[Dict[Point, Dict[Point, int]]] = []
        for layout in self.env.layouts:
            self.distance_maps.append(self._compute_all_pairs(layout))

    def _compute_all_pairs(self, layout: PacmanLayout) -> Dict[Point, Dict[Point, int]]:
        passable = [
            (r, c)
            for r in range(layout.height)
            for c in range(layout.width)
            if not layout.is_wall((r, c))
        ]
        distances: Dict[Point, Dict[Point, int]] = {}
        for cell in passable:
            distances[cell] = self._bfs_exact(layout, cell)
        return distances

    def _bfs_exact(self, layout: PacmanLayout, start: Point) -> Dict[Point, int]:
        queue: deque[Tuple[Point, int]] = deque([(start, 0)])
        visited = {start}
        dists = {start: 0}

        while queue:
            pos, dist = queue.popleft()
            for nb in _neighbors(layout, pos):
                if nb in visited:
                    continue
                visited.add(nb)
                dists[nb] = dist + 1
                queue.append((nb, dist + 1))

        return dists

    def _distance(self, layout_index: int, start: Point, goal: Point) -> int:
        dist = self.distance_maps[layout_index].get(start, {}).get(goal)
        if dist is None:
            return 0
        return dist

    def _mst_cost(self, layout_index: int, points: List[Point]) -> int:
        if len(points) <= 1:
            return 0

        visited = {points[0]}
        edges = []
        for other in points[1:]:
            dist = self._distance(layout_index, points[0], other)
            heapq.heappush(edges, (dist, points[0], other))

        total = 0
        while edges and len(visited) < len(points):
            weight, _, node = heapq.heappop(edges)
            if node in visited:
                continue
            visited.add(node)
            total += weight
            for other in points:
                if other not in visited:
                    dist = self._distance(layout_index, node, other)
                    heapq.heappush(edges, (dist, node, other))

        return total

    def calculate(self, state: PacmanState) -> int:
        if state.pie_timer > 0:
            return 0  # để đảm bảo admissible khi có khả năng xuyên tường

        layout_index = state.layout_index
        layout = self.env.layouts[layout_index]

        if not state.food:
            return self._distance(layout_index, state.pacman_pos, layout.exit_gate)

        pacman_to_food = min(
            self._distance(layout_index, state.pacman_pos, food)
            for food in state.food
        )

        targets = list(state.food) + [layout.exit_gate]
        mst_cost = self._mst_cost(layout_index, targets)
        return pacman_to_food + mst_cost


class ExactMSTHeuristic(Heuristic):
    """
    H₁: Exact + MST + hỗ trợ xuyên tường
    - Dùng BFS thật (có tường, teleport) để tính metric chính xác.
    - Thêm metric 'free' (bỏ tường) để làm cận dưới khi pie cho phép xuyên tường.
    - Heuristic = min( h_exact, h_free ) với h = minDist + MST theo metric tương ứng.
    """

    def __init__(self, environment: PacmanEnvironment):
        self.env = environment
        self._bfs_cache_exact: Dict[Tuple[int, Point], Dict[Point, int]] = {}
        self._bfs_cache_free: Dict[Tuple[int, Point], Dict[Point, int]] = {}

    def calculate(self, state: PacmanState) -> int:
        layout_index = state.layout_index
        layout = self.env.layouts[layout_index]

        def h_with(dist_fn):
            if not state.food:
                return dist_fn(layout_index, state.pacman_pos, layout.exit_gate)
            pac_to_food = min(dist_fn(layout_index, state.pacman_pos, food) for food in state.food)
            targets = list(state.food) + [layout.exit_gate]
            mst = self._mst_cost_with(layout_index, targets, dist_fn)
            return pac_to_food + mst

        h_exact = h_with(self._dist_exact)
        h_free = h_with(self._dist_free)
        return min(h_exact, h_free)

    # ---- Neighbours ----
    def _neighbors_exact(self, layout: PacmanLayout, pos: Point) -> Iterable[Point]:
        r, c = pos
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nb = (r + dr, c + dc)
            if layout.in_bounds(nb) and not layout.is_wall(nb):
                yield nb
        if layout.corner_name(pos):
            for _, corner in layout.teleports.items():
                if corner != pos and not layout.is_wall(corner):
                    yield corner

    def _neighbors_free(self, layout: PacmanLayout, pos: Point) -> Iterable[Point]:
        r, c = pos
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nb = (r + dr, c + dc)
            if layout.in_bounds(nb):
                yield nb
        if layout.corner_name(pos):
            for _, corner in layout.teleports.items():
                if corner != pos:
                    yield corner

    # ---- BFS cache ----
    def _bfs_exact(self, layout_index: int, start: Point) -> Dict[Point, int]:
        key = (layout_index, start)
        if key in self._bfs_cache_exact:
            return self._bfs_cache_exact[key]

        layout = self.env.layouts[layout_index]
        q: Deque[Point] = deque([start])
        dist: Dict[Point, int] = {start: 0}
        while q:
            u = q.popleft()
            for v in self._neighbors_exact(layout, u):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        self._bfs_cache_exact[key] = dist
        return dist

    def _bfs_free(self, layout_index: int, start: Point) -> Dict[Point, int]:
        key = (layout_index, start)
        if key in self._bfs_cache_free:
            return self._bfs_cache_free[key]

        layout = self.env.layouts[layout_index]
        q: Deque[Point] = deque([start])
        dist: Dict[Point, int] = {start: 0}
        while q:
            u = q.popleft()
            for v in self._neighbors_free(layout, u):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        self._bfs_cache_free[key] = dist
        return dist

    def _dist_exact(self, layout_index: int, a: Point, b: Point) -> int:
        if a == b:
            return 0
        return self._bfs_exact(layout_index, a).get(b, 0)

    def _dist_free(self, layout_index: int, a: Point, b: Point) -> int:
        if a == b:
            return 0
        return self._bfs_free(layout_index, a).get(b, 0)

    # ---- MST ----
    def _mst_cost_with(self, layout_index: int, points: List[Point], dist_fn) -> int:
        if len(points) <= 1:
            return 0

        visited = {points[0]}
        edges: List[Tuple[int, Point, Point]] = []
        for other in points[1:]:
            w = dist_fn(layout_index, points[0], other)
            heapq.heappush(edges, (w, points[0], other))

        total = 0
        while edges and len(visited) < len(points):
            w, _, v = heapq.heappop(edges)
            if v in visited:
                continue
            visited.add(v)
            total += w
            for other in points:
                if other not in visited:
                    heapq.heappush(edges, (dist_fn(layout_index, v, other), v, other))
        return total


class CombinedHeuristic(Heuristic):
    """Lấy max giữa các heuristic để tăng thông tin nhưng vẫn admissible."""

    def __init__(self, environment: PacmanEnvironment):
        self.pie = PieAwareHeuristic(environment)
        self.mst = FoodMSTHeuristic(environment)
        self.exact = ExactDistanceHeuristic(environment)
        self.h1 = ExactMSTHeuristic(environment)

    def calculate(self, state: PacmanState) -> int:
        return max(
            self.pie.calculate(state),
            self.mst.calculate(state),
            self.exact.calculate(state),
            self.h1.calculate(state),
        )


__all__ = [
    "PieAwareHeuristic",
    "FoodMSTHeuristic",
    "ExactDistanceHeuristic",
    "ExactMSTHeuristic",
    "CombinedHeuristic",
]
