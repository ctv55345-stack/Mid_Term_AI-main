"""
Main entry point for 8-puzzle solver
"""
import os
from datetime import datetime
from typing import List
from models import State
from algorithms import Problem, AStar
from algorithms.heuristic import MisplacedTilesHeuristic, ManhattanDistanceHeuristic
from utils import Visualizer
from tests.test_cases import TestCases
from config import Config


def solve_puzzle(board: List[List[int]], heuristic_classes: list, test_case_name: str, difficulty: str, show_path=True):    
    initial_state = State(board)
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    filename = f"{results_dir}/{difficulty}_{test_case_name}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("GIẢI PUZZLE 8 - THUẬT TOÁN A*\n")
        f.write("="*60 + "\n")
        f.write(f"Test Case: {test_case_name}\n")
        f.write(f"Độ khó: {difficulty}\n")
        f.write(f"Thời gian tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n" + "="*60 + "\n")
        f.write("TRẠNG THÁI BAN ĐẦU:\n")
        f.write(str(initial_state) + "\n")
        
        problem = Problem(initial_state)
        results = {}
        
        for heuristic_class in heuristic_classes:
            f.write(f"\n{'='*60}\n")
            f.write(f"Chạy với {heuristic_class.__name__}\n")
            f.write('='*60 + "\n")
            
            heuristic = heuristic_class(problem.goal_states)
            astar = AStar(problem, heuristic)
            path, cost, stats = astar.search()
            
            if path is not None:
                f.write(f"[THÀNH CÔNG] Tìm thấy lời giải!\n")
                f.write(f"  - Chi phí: {cost} bước\n")
                f.write(f"  - Số nút đã mở rộng: {stats['nodes_expanded']}\n")
                f.write(f"  - Kích thước frontier tối đa: {stats['max_frontier_size']}\n")
                f.write(f"  - Thời gian: {stats['time']:.4f}s\n")
                
                results[heuristic_class.__name__] = stats
                
                if show_path:
                    f.write("\nĐƯỜNG ĐI GIẢI:\n")
                    f.write("-" * 40 + "\n")
                    
                    # Show initial state
                    f.write(f"Trạng thái ban đầu: {initial_state}")
                    
                    # Show each step with matrix state
                    current_state = initial_state
                    for i, action in enumerate(path):
                        f.write(f"\nBước {i+1}: {action}\n")
                        current_state = current_state.apply_action(action)
                        f.write(f"Sau bước {i+1}: {current_state}")
                    
                    # Show final goal state
                    f.write(f"\nTRẠNG THÁI ĐÍCH CUỐI CÙNG: {current_state}")
                    f.write("=" * 40 + "\n")
            else:
                f.write(f"[THẤT BẠI] Không tìm thấy lời giải!\n")
        
        if Config.SHOW_COMPARISON and len(results) > 1:
            f.write(f"\n{'='*60}\n")
            f.write("SO SÁNH CÁC HEURISTIC\n")
            f.write('='*60 + "\n")
            for name, stats in results.items():
                f.write(f"{name}:\n")
                f.write(f"  - Số nút đã mở rộng: {stats['nodes_expanded']}\n")
                f.write(f"  - Kích thước frontier tối đa: {stats['max_frontier_size']}\n")
                f.write(f"  - Thời gian: {stats['time']:.4f}s\n")
    
    print(f"[OK] Da luu ket qua vao: {filename}")
    return results


def run_tests():
    """Run all test cases and save results to individual files"""
    
    print("="*60)
    print("GIAI PUZZLE 8 - THUAT TOAN A*")
    print("="*60)
    print("Ket qua se duoc luu vao cac file .txt rieng trong thu muc 'results'")
    print("="*60)
    
    heuristics = [MisplacedTilesHeuristic, ManhattanDistanceHeuristic]
    
    if Config.RUN_EASY_TESTS:
        print("\n\n" + "="*60)
        print("CAC TEST CASE DE")
        print("="*60)
        
        for i, board in enumerate(TestCases.get_easy_cases(), 1):
            test_case_name = f"easy_case_{i:02d}"
            print(f"\n Dang xu ly {test_case_name}")
            solve_puzzle(board, heuristics, test_case_name, "de", show_path=True)
    
    if Config.RUN_MEDIUM_TESTS:
        print("\n\n" + "="*60)
        print("CAC TEST CASE TRUNG BINH")
        print("="*60)
        
        for i, board in enumerate(TestCases.get_medium_cases(), 1):
            test_case_name = f"medium_case_{i:02d}"
            print(f"\n Dang xu ly {test_case_name}")
            solve_puzzle(board, heuristics, test_case_name, "trung binh", show_path=True)
    
    if Config.RUN_HARD_TESTS:
        print("\n\n" + "="*60)
        print("CAC TEST CASE KHO")
        print("="*60)
        
        for i, board in enumerate(TestCases.get_hard_cases(), 1):
            test_case_name = f"hard_case_{i:02d}"
            print(f"\n Dang xu ly {test_case_name}")
            solve_puzzle(board, heuristics, test_case_name, "kho", show_path=True)
    
    print("\n" + "="*60)
    print("HOAN THANH TAT CA TEST CASES!")
    print("Kiem tra thu muc 'results' de xem cac file loi giai rieng biet.")
    print("="*60)


def main():
    """Main function"""
    run_tests()


if __name__ == "__main__":
    main()