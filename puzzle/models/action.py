"""
Action representation for 8-puzzle
"""
from typing import Tuple


class Action:
    """Game action"""
    
    def __init__(self, action_type: str, pos1: Tuple[int, int], pos2: Tuple[int, int]):
        self.type = action_type
        self.pos1 = pos1
        self.pos2 = pos2
    
    def __str__(self):
        return f"{self.type}: {self.pos1} <-> {self.pos2}"
    
    def __repr__(self):
        return self.__str__()