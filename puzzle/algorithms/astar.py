"""
A* Search Algorithm implementation
"""
import heapq
import time
from typing import List, Tuple, Optional, Dict
from models.node import Node
from models.action import Action
from algorithms.problem import Problem
from algorithms.heuristic import Heuristic


class AStar:
    """A* search algorithm"""
    
    def __init__(self, problem: Problem, heuristic: Heuristic):
        self.problem = problem
        self.heuristic = heuristic
        self.nodes_expanded = 0
        self.max_frontier_size = 0
    
    def search(self) -> Tuple[Optional[List[Action]], int, Dict]:
        """Search for solution. Returns: (path, cost, statistics)"""
        start_time = time.time()
        
        if self.problem.is_goal(self.problem.initial_state):
            end_time = time.time()
            return [], 0, {
                'nodes_expanded': 0,
                'max_frontier_size': 0,
                'time': end_time - start_time,
                'solution_depth': 0
            }
        
        h = self.heuristic.calculate(self.problem.initial_state)
        initial_node = Node(self.problem.initial_state, None, None, 0, h)
        
        frontier = []
        heapq.heappush(frontier, initial_node)
        
        explored = set()
        frontier_states = {initial_node.state.to_tuple(): initial_node}
        
        while frontier:
            current_node = heapq.heappop(frontier)
            current_state_tuple = current_node.state.to_tuple()
            
            if current_state_tuple in frontier_states:
                del frontier_states[current_state_tuple]
            
            if self.problem.is_goal(current_node.state):
                end_time = time.time()
                stats = {
                    'nodes_expanded': self.nodes_expanded,
                    'max_frontier_size': self.max_frontier_size,
                    'time': end_time - start_time,
                    'solution_depth': current_node.path_cost
                }
                return current_node.get_path(), current_node.path_cost, stats
            
            explored.add(current_state_tuple)
            self.nodes_expanded += 1
            
            for next_state, action, cost in self.problem.get_successors(current_node.state):
                next_state_tuple = next_state.to_tuple()
                
                if next_state_tuple in explored:
                    continue
                
                g = current_node.path_cost + cost
                h = self.heuristic.calculate(next_state)
                child_node = Node(next_state, current_node, action, g, h)
                
                if next_state_tuple in frontier_states:
                    existing_node = frontier_states[next_state_tuple]
                    if child_node.f_score < existing_node.f_score:
                        frontier_states[next_state_tuple] = child_node
                        heapq.heappush(frontier, child_node)
                else:
                    frontier_states[next_state_tuple] = child_node
                    heapq.heappush(frontier, child_node)
            
            self.max_frontier_size = max(self.max_frontier_size, len(frontier))
        
        end_time = time.time()
        return None, -1, {
            'nodes_expanded': self.nodes_expanded,
            'time': end_time - start_time
        }