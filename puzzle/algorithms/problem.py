"""
Problem formulation for search algorithms
"""
from typing import List, Tuple
from models.state import State
from models.action import Action
from config import PuzzleConfig


class Problem:
    """Problem definition"""
    
    def __init__(self, initial_state: State, goal_states: List[List[List[int]]] = None):
        self.initial_state = initial_state
        
        if goal_states is None:
            goal_states = PuzzleConfig.GOAL_STATES
        
        self.goal_states = [State(goal) for goal in goal_states]
    
    def is_goal(self, state: State) -> bool:
        """Check if state is goal"""
        for goal in self.goal_states:
            if state.board == goal.board:
                return True
        return False
    
    def get_successors(self, state: State) -> List[Tuple[State, Action, int]]:
        """Get successor states"""
        successors = []
        
        actions = state.get_valid_actions()
        
        for action in actions:
            next_state = state.apply_action(action)
            cost = 1
            successors.append((next_state, action, cost))
        
        return successors