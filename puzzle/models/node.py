"""
Node for search tree
"""
from typing import List, Optional
from models.state import State
from models.action import Action


class Node:
    """Search tree node"""
    
    def __init__(self, state: State, parent: Optional['Node'], 
                 action: Optional[Action], path_cost: int, heuristic: int):
        self.state = state
        self.parent = parent
        self.action = action
        self.path_cost = path_cost  # g(n)
        self.heuristic = heuristic  # h(n)
        self.f_score = path_cost + heuristic  # f(n) = g(n) + h(n)
    
    def get_path(self) -> List[Action]:
        """Trace path from root to current node"""
        path = []
        current = self
        while current.parent is not None:
            path.append(current.action)
            current = current.parent
        return list(reversed(path))
    
    def __lt__(self, other):
        """Comparison for priority queue"""
        return self.f_score < other.f_score