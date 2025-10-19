"""
State representation for 8-puzzle
"""
from typing import List, Tuple
from copy import deepcopy
from models.action import Action


class State:
    def __init__(self, board: List[List[int]]):
        self.board = board
        self.blank_pos = self._find_blank()

    def _find_blank(self) -> Tuple[int, int]:
        for i in range(3):
            for j in range(3):
                if self.board[i][j] == 0:
                    return (i, j)
        return (0, 0)

    def get_valid_actions(self) -> List[Action]:
        actions = []

        # Original move UDLR
        blank = self.blank_pos
        if (blank[0] > 0):
            actions.append(Action("move_up", blank, (blank[0] - 1, blank[1])))
        if (blank[0] < 2):
            actions.append(Action("move_down", blank, (blank[0] + 1, blank[1])))
        if (blank[1] > 0):
            actions.append(Action("move_left", blank, (blank[0], blank[1] - 1)))
        if (blank[1] < 2):
            actions.append(Action("move_right", blank, (blank[0], blank[1] + 1)))

        # Rule 1: Swap A + B = 9
        for i in range(3):
            for j in range(3):
                if self.board[i][j] == 0:
                    continue

                # Check right neighbor
                if j < 2:
                    neighbor = self.board[i][j+1]
                    if neighbor != 0 and self.board[i][j] + neighbor == 9:
                        actions.append(Action("sum9_swap", (i, j), (i, j+1)))

                # Check bottom neighbor
                if i < 2:
                    neighbor = self.board[i+1][j]
                    if neighbor != 0 and self.board[i][j] + neighbor == 9:
                        actions.append(Action("sum9_swap", (i, j), (i+1, j)))

        # Rule 2: Corner diagonal swaps
        if self.board[0][0] != 0 and self.board[2][2] != 0:
            actions.append(Action("corner_swap", (0, 0), (2, 2)))

        if self.board[0][2] != 0 and self.board[2][0] != 0:
            actions.append(Action("corner_swap", (0, 2), (2, 0)))

        return actions

    def apply_action(self, action: Action) -> 'State':
        new_board = deepcopy(self.board)
        (r1, c1), (r2, c2) = action.pos1, action.pos2
        new_board[r1][c1], new_board[r2][c2] = new_board[r2][c2], new_board[r1][c1]
        return State(new_board)

    def to_tuple(self) -> Tuple:
        return tuple(tuple(row) for row in self.board)

    def __eq__(self, other):
        return self.board == other.board

    def __hash__(self):
        return hash(self.to_tuple())

    def __str__(self):
        result = "\n"
        for row in self.board:
            result += " ".join(str(x) if x != 0 else "_" for x in row) + "\n"
        return result