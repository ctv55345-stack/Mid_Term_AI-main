"""
Heuristic functions for A* algorithm
"""
from typing import List
from models.state import State


class Heuristic:
    """Base class for heuristics"""
    
    def __init__(self, goal_states: List[State]):
        self.goal_states = goal_states
    
    def calculate(self, state: State) -> int:
        raise NotImplementedError
    
    def name(self) -> str:
        return self.__class__.__name__


class MisplacedTilesHeuristic(Heuristic):
    """Count misplaced tiles"""
    
    def calculate(self, state: State) -> int:
        min_misplaced = float('inf')
        
        for goal in self.goal_states:
            misplaced = 0
            for i in range(3):
                for j in range(3):
                    if state.board[i][j] != 0 and state.board[i][j] != goal.board[i][j]:
                        misplaced += 1
            min_misplaced = min(min_misplaced, misplaced)
        
        return int(min_misplaced)


class ManhattanDistanceHeuristic(Heuristic):
    """Manhattan distance heuristic"""
    
    def calculate(self, state: State) -> int:
        min_distance = float('inf')
        
        for goal in self.goal_states:
            total_distance = 0
            
            goal_positions = {}
            for i in range(3):
                for j in range(3):
                    if goal.board[i][j] != 0:
                        goal_positions[goal.board[i][j]] = (i, j)
            
            for i in range(3):
                for j in range(3):
                    tile = state.board[i][j]
                    if tile != 0 and tile in goal_positions:
                        goal_i, goal_j = goal_positions[tile]
                        total_distance += abs(i - goal_i) + abs(j - goal_j)
            
            min_distance = min(min_distance, total_distance)
        
        return int(min_distance)