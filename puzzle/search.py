from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Action:
    """Hành động tổng quát.

    - `type`: nhãn hành động (vd: move_up, Teleport, …)
    - `pos1`, `pos2`: tùy chọn
    - `payload`: dict tùy chọn chứa thông tin bổ sung
    """

    type: str
    pos1: Optional[Tuple[int, int]] = None
    pos2: Optional[Tuple[int, int]] = None
    payload: Optional[Dict[str, object]] = None

    def __str__(self) -> str:
        parts = [self.type]
        if self.pos1 is not None and self.pos2 is not None:
            parts.append(f"{self.pos1}->{self.pos2}")
        if self.payload:
            parts.append(str(self.payload))
        return ":".join(parts)


@dataclass
class Node:
    """Nút trong cây tìm kiếm."""
    state: object
    parent: Optional["Node"]
    action: Optional[Action]
    path_cost: int
    heuristic: int

    @property
    def f_score(self) -> int:
        return self.path_cost + self.heuristic

    def get_path(self) -> List[Action]:
        path: List[Action] = []
        node: Optional[Node] = self
        while node and node.parent is not None:
            if node.action is not None:
                path.append(node.action)
            node = node.parent
        return list(reversed(path))

    def __lt__(self, other: "Node") -> bool:
        return self.f_score < other.f_score


class Problem:
    """Lớp cơ sở cho mọi bài toán tìm kiếm."""

    def __init__(self, initial_state: object):
        self.initial_state = initial_state

    def is_goal(self, state: object) -> bool:  
        raise NotImplementedError

    def get_successors(self, state: object) -> Sequence[Tuple[object, Action, int]]:  
        raise NotImplementedError


class Heuristic:
    def calculate(self, state: object) -> int:  
        raise NotImplementedError

    def name(self) -> str:
        return self.__class__.__name__


class AStar:
    """Thuật toán A* tổng quát"""

    def __init__(self, problem: Problem, heuristic: Heuristic):
        self.problem = problem
        self.heuristic = heuristic

    def search(self) -> Tuple[Optional[List[Action]], int, int, int]:
        """Trả về (đường đi, chi phí, số nút expanded, frontier tối đa)."""
        if self.problem.is_goal(self.problem.initial_state):
            return [], 0, 0, 1

        initial_h = self.heuristic.calculate(self.problem.initial_state)
        initial_node = Node(self.problem.initial_state, None, None, 0, initial_h)

        frontier: List[Node] = []
        heapq.heappush(frontier, initial_node)
        frontier_lookup = {self.problem.initial_state: initial_node}
        explored: Dict[object, int] = {}
        max_frontier_size = 1

        while frontier:
            max_frontier_size = max(max_frontier_size, len(frontier))
            current_node = heapq.heappop(frontier)
            state = current_node.state
            frontier_lookup.pop(state, None)

            if self.problem.is_goal(state):
                return (
                    current_node.get_path(),
                    current_node.path_cost,
                    len(explored),
                    max_frontier_size,
                )

            explored[state] = current_node.path_cost

            for next_state, action, cost in self.problem.get_successors(state):
                new_cost = current_node.path_cost + cost
                if next_state in explored and explored[next_state] <= new_cost:
                    continue

                heuristic_cost = self.heuristic.calculate(next_state)
                child = Node(next_state, current_node, action, new_cost, heuristic_cost)

                existing = frontier_lookup.get(next_state)
                if existing is None or child.f_score < existing.f_score:
                    frontier_lookup[next_state] = child
                    heapq.heappush(frontier, child)

        return None, -1, len(explored), max_frontier_size


__all__ = ["Action", "Node", "Problem", "Heuristic", "AStar"]
