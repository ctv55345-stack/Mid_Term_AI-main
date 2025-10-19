"""
Visualization utilities
"""
from typing import List
from models.state import State
from models.action import Action


class Visualizer:
    """Result visualization tool"""
    
    @staticmethod
    def print_solution(initial_state: State, path: List[Action]):
        """Print complete solution path"""
        print("\n" + "="*50)
        print("SOLUTION PATH")
        print("="*50)
        
        current = initial_state
        print(f"\nStep 0 (Initial):{current}")
        
        for i, action in enumerate(path, 1):
            current = current.apply_action(action)
            print(f"Step {i}: {action}")
            print(current)
        
        print("="*50)
    
    @staticmethod
    def print_statistics(stats: dict, heuristic_name: str):
        """Print statistics"""
        print(f"\n--- Statistics ({heuristic_name}) ---")
        print(f"  Nodes expanded: {stats['nodes_expanded']}")
        print(f"  Max frontier size: {stats.get('max_frontier_size', 'N/A')}")
        print(f"  Solution depth: {stats.get('solution_depth', 'N/A')}")
        print(f"  Time: {stats['time']:.4f}s")
    
    @staticmethod
    def compare_heuristics(results: dict):
        """Compare heuristics"""
        print("\n" + "="*50)
        print("HEURISTIC COMPARISON")
        print("="*50)
        
        for name, stats in results.items():
            print(f"\n{name}:")
            print(f"  Nodes: {stats['nodes_expanded']}")
            print(f"  Time: {stats['time']:.4f}s")
        
        best_nodes = min(results.items(), key=lambda x: x[1]['nodes_expanded'])
        best_time = min(results.items(), key=lambda x: x[1]['time'])
        
        print(f"\n Best (Nodes): {best_nodes[0]}")
        print(f" Best (Time): {best_time[0]}")
        print("="*50)