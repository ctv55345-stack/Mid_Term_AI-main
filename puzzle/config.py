class PuzzleConfig:    
    GOAL_STATES = [
        [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        [[8, 7, 6], [5, 4, 3], [2, 1, 0]],
        [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        [[0, 8, 7], [6, 5, 4], [3, 2, 1]]
    ]
    
    MAX_ITERATIONS = 100000


class Config:    
    SHOW_DETAILED_PATH = True
    SHOW_STATISTICS = True
    SHOW_COMPARISON = True
    
    RUN_EASY_TESTS = True
    RUN_MEDIUM_TESTS = True
    RUN_HARD_TESTS = True
    
    HEURISTICS = [
        'MisplacedTilesHeuristic',
        'ManhattanDistanceHeuristic'
    ]