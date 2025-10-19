from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from puzzle import Action, Problem


Point = Tuple[int, int]


@dataclass(frozen=True)
class GhostState:
    """Trạng thái của ma: vị trí và hướng di chuyển theo cột."""

    position: Point
    direction: int  # +1: sang phải, -1: sang trái


@dataclass(frozen=True)
class PacmanState:
    """Trạng thái đầy đủ của Pacman."""

    pacman_pos: Point
    food: FrozenSet[Point]
    pies: FrozenSet[Point]
    ghosts: Tuple[GhostState, ...]
    pie_timer: int
    time_step: int
    layout_index: int
    


@dataclass(frozen=True)
class PacmanLayout:
    """Bố cục của mê cung ở một góc quay nhất định."""

    width: int
    height: int
    walls: FrozenSet[Point]
    food: FrozenSet[Point]
    pies: FrozenSet[Point]
    teleports: Dict[str, Point]
    exit_gate: Point
    pacman_start: Point
    ghost_starts: Tuple[GhostState, ...]

    def in_bounds(self, pos: Point) -> bool:
        r, c = pos
        return 0 <= r < self.height and 0 <= c < self.width

    def is_wall(self, pos: Point) -> bool:
        return pos in self.walls

    def corner_name(self, pos: Point) -> Optional[str]:
        for name, corner in self.teleports.items():
            if corner == pos:
                return name
        return None
    
    def to_list(self) -> List[str]:
        output = []
        element_map = {
            "walls": self.walls,
            "food": self.food,
            "pies": self.pies,
            "exit_gate": self.exit_gate,
            "pacman_start": self.pacman_start,
            "ghost_starts": {g.position for g in self.ghost_starts},
        }
        
        for r in range(self.height):
            row = []
            for c in range(self.width):
                pos = (r, c)
                if pos in element_map["walls"]:
                    row.append('%')
                elif pos in element_map["food"]:
                    row.append('.')
                elif pos in element_map["pies"]:
                    row.append('O')
                elif pos == element_map["exit_gate"]:
                    row.append('E')
                elif pos == element_map["pacman_start"]:
                    row.append('P')
                elif pos in element_map["ghost_starts"]:
                    row.append('G')
                else:
                    row.append(' ')
            output.append(''.join(row))
        return output

def _rotate_point(point: Point, width: int, height: int) -> Point:
    r, c = point
    return c, height - 1 - r


def _rotate_layout(layout: PacmanLayout) -> PacmanLayout:
    """Sinh layout sau khi quay 90 độ theo chiều kim đồng hồ."""
    new_width, new_height = layout.height, layout.width
    rotate = lambda p: _rotate_point(p, layout.width, layout.height)

    return PacmanLayout(
        width=new_width,
        height=new_height,
        walls=frozenset(rotate(p) for p in layout.walls),
        food=frozenset(rotate(p) for p in layout.food),
        pies=frozenset(rotate(p) for p in layout.pies),
        teleports={name: rotate(pos) for name, pos in layout.teleports.items()},
        exit_gate=rotate(layout.exit_gate),
        pacman_start=rotate(layout.pacman_start),
        ghost_starts=tuple(GhostState(rotate(g.position), 1) for g in layout.ghost_starts),
    )



class PacmanEnvironment:
    """Quản lý layout và trạng thái khởi tạo của Pacman."""

    PIE_DURATION = 5
    ROTATION_PERIOD = 30

    def __init__(self, layout_lines: Sequence[str]):
        base_layout = self._parse_layout(layout_lines)
        self.layouts: List[PacmanLayout] = [base_layout]
        for _ in range(3):
            self.layouts.append(_rotate_layout(self.layouts[-1]))

            start_layout = self.layouts[0]
        self.initial_state = PacmanState(
            pacman_pos=start_layout.pacman_start,
            food=start_layout.food,
            pies=start_layout.pies,
            ghosts=start_layout.ghost_starts,
            pie_timer=0,
            time_step=0,
            layout_index=0,
        )

    def _parse_layout(self, lines: Sequence[str]) -> PacmanLayout:
        width = max(len(line) for line in lines)
        height = len(lines)

        walls: List[Point] = []
        food: List[Point] = []
        pies: List[Point] = []
        ghosts: List[GhostState] = []
        exit_gate: Optional[Point] = None
        pacman_start: Optional[Point] = None

        padded = [line.ljust(width) for line in lines]
        for r, line in enumerate(padded):
            for c, ch in enumerate(line):
                pos = (r, c)
                if ch == "%":
                    walls.append(pos)
                elif ch == ".":
                    food.append(pos)
                elif ch == "O":
                    pies.append(pos)
                elif ch == "G":
                    ghosts.append(GhostState(pos, 1))
                elif ch == "E":
                    exit_gate = pos
                elif ch == "P":
                    pacman_start = pos

        teleports = self._find_teleport_corners(width, height, set(walls))

        if exit_gate is None or pacman_start is None:
            raise ValueError("Layout phải chứa ký tự 'P' và 'E'.")

        return PacmanLayout(
            width=width,
            height=height,
            walls=frozenset(walls),
            food=frozenset(food),
            pies=frozenset(pies),
            teleports=teleports,
            exit_gate=exit_gate,
            pacman_start=pacman_start,
            ghost_starts=tuple(ghosts),
        )

    def _find_teleport_corners(self, width: int, height: int, walls: set) -> Dict[str, Point]:
        """
        ✓ TÌM TELEPORT CORNERS THÔNG MINH
        - Ưu tiên: Góc không có tường
        - Fallback: Ô gần góc nhất (trong vòng 3x3)
        """        
        corner_regions = {
            "TL": {  # Top-Left
                "ideal": (0, 0),
                "search": [(r, c) for r in range(3) for c in range(3)],
            },
            "TR": {  # Top-Right
                "ideal": (0, width - 1),
                "search": [(r, width - 1 - c) for r in range(3) for c in range(3)],
            },
            "BL": {  # Bottom-Left
                "ideal": (height - 1, 0),
                "search": [(height - 1 - r, c) for r in range(3) for c in range(3)],
            },
            "BR": {  # Bottom-Right
                "ideal": (height - 1, width - 1),
                "search": [(height - 1 - r, width - 1 - c) for r in range(3) for c in range(3)],
            },
        }
        
        teleports = {}
        
        for corner_name, region in corner_regions.items():
            ideal_pos = region["ideal"]
            
            if ideal_pos not in walls:
                teleports[corner_name] = ideal_pos
                print(f"{corner_name}: {ideal_pos} (ideal corner)")
                continue
            
            found = False
            for pos in region["search"]:
                r, c = pos
                if 0 <= r < height and 0 <= c < width:
                    if pos not in walls:
                        teleports[corner_name] = pos
                        print(f"{corner_name}: {pos} (near corner, offset from {ideal_pos})")
                        found = True
                        break
            
            if not found:
                print(f"{corner_name}: No valid position found")
        
        print(f"Total teleport points: {len(teleports)}/4")
        return teleports

    def rotate_state(self, state: PacmanState) -> PacmanState:
        layout = self.layouts[state.layout_index]
        next_index = (state.layout_index + 1) % 4
        rotate = lambda p: _rotate_point(p, layout.width, layout.height)

        return PacmanState(
            pacman_pos=rotate(state.pacman_pos),
            food=frozenset(rotate(p) for p in state.food),
            pies=frozenset(rotate(p) for p in state.pies),
            ghosts=tuple(GhostState(rotate(g.position), 1) for g in state.ghosts),
            pie_timer=state.pie_timer,
            time_step=state.time_step,
            layout_index=next_index,
        )
    
    def to_list(self)-> List[str]:
        layout = self.layouts[0]
        height = layout.height
        width = layout.width
            
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        for (x, y) in self.layouts[0].walls:
            grid[x][y] = '%'
            
        state = self.initial_state
        
        for (x, y) in state.food:
            grid[x][y] = '.'
            
        for (x, y) in state.pies:
            grid[x][y] = 'O'
            
        for g in state.ghosts:
            grid[g.position[0]][g.position[1]] = 'G'
            
        grid[state.pacman_pos[0]][state.pacman_pos[1]] = 'P'
        return [''.join(row) for row in grid]
    


class PacmanProblem(Problem):
    MOVE_DELTAS: Dict[str, Point] = {
        "Up": (-1, 0),
        "Down": (1, 0),
        "Left": (0, -1),
        "Right": (0, 1),
        "Stop": (0, 0),
    }

    def __init__(self, environment: PacmanEnvironment):
        super().__init__(environment.initial_state)
        self.env = environment

    def is_goal(self, state: PacmanState) -> bool:
        layout = self.env.layouts[state.layout_index]
        return not state.food and state.pacman_pos == layout.exit_gate

    def get_successors(self, state: PacmanState):
        layout = self.env.layouts[state.layout_index]
        successors: List[Tuple[PacmanState, Action, int]] = []

        for move_name, delta in self.MOVE_DELTAS.items():
            successors.extend(self._apply_move(state, layout, move_name, delta))

        if layout.corner_name(state.pacman_pos):
            for _, target in layout.teleports.items():
                if target != state.pacman_pos:
                    teleported = self._apply_teleport(state, layout, target)
                    if teleported is not None:
                        successors.append((teleported, Action("Teleport", payload={"to": target}), 1))

        return successors
    

    def _apply_move(
        self,
        state: PacmanState,
        layout: PacmanLayout,
        move_name: str,
        delta: Point,
    ) -> Iterable[Tuple[PacmanState, Action, int]]:
        dr, dc = delta
        new_pos = (state.pacman_pos[0] + dr, state.pacman_pos[1] + dc)
        

        if not layout.in_bounds(new_pos):
            return []
        if layout.is_wall(new_pos) and state.pie_timer <= 0:
            return []
        if any(g.position == new_pos for g in state.ghosts):
            return []

        pie_timer = max(state.pie_timer - 1, 0) if move_name != "Stop" else state.pie_timer
        remaining_pies = state.pies
        if new_pos in state.pies:
            pie_timer = self.env.PIE_DURATION
            remaining_pies = frozenset(p for p in state.pies if p != new_pos)

        remaining_food = state.food
        if new_pos in state.food:
            remaining_food = frozenset(p for p in state.food if p != new_pos)

        ghosts = tuple(self._move_ghost(g, layout) for g in state.ghosts)
        if any(g.position == new_pos for g in ghosts):
            return []
        
        ghosts_next = tuple(self._move_ghost(g, layout) for g in state.ghosts)
        if any(g.position == new_pos for g in ghosts_next):
            return []
        

        next_time = state.time_step + 1
        next_state = PacmanState(
            pacman_pos=new_pos,
            food=remaining_food,
            pies=remaining_pies,
            ghosts=ghosts,
            pie_timer=pie_timer,
            time_step=next_time,
            layout_index=state.layout_index,
        )

        if next_time % self.env.ROTATION_PERIOD == 0:
            next_state = self.env.rotate_state(next_state)

        return [(next_state, Action(move_name), 1)]

    def _apply_teleport(
        self,
        state: PacmanState,
        layout: PacmanLayout,
        target: Point,
    ) -> Optional[PacmanState]:
        if any(g.position == target for g in state.ghosts):
            return None

        pie_timer = max(state.pie_timer - 1, 0)
        remaining_food = state.food
        remaining_pies = state.pies
        if target in remaining_food:
            remaining_food = frozenset(p for p in remaining_food if p != target)
        if target in remaining_pies:
            pie_timer = self.env.PIE_DURATION
            remaining_pies = frozenset(p for p in remaining_pies if p != target)

        ghosts = tuple(self._move_ghost(g, layout) for g in state.ghosts)
        if any(g.position == target for g in ghosts):
            return None

        next_time = state.time_step + 1
        new_state = PacmanState(
            pacman_pos=target,
            food=remaining_food,
            pies=remaining_pies,
            ghosts=ghosts,
            pie_timer=pie_timer,
            time_step=next_time,
            layout_index=state.layout_index,
        )
        if next_time % self.env.ROTATION_PERIOD == 0:
            new_state = self.env.rotate_state(new_state)
        return new_state

    def _move_ghost(self, ghost: GhostState, layout: PacmanLayout) -> GhostState:
        row, col = ghost.position
        next_col = col + ghost.direction
        next_pos = (row, next_col)
        if not layout.in_bounds(next_pos) or layout.is_wall(next_pos):
            ghost = GhostState(ghost.position, -ghost.direction)
            next_pos = (row, col + ghost.direction)

        if not layout.in_bounds(next_pos) or layout.is_wall(next_pos):
            return GhostState(ghost.position, ghost.direction)

        return GhostState(next_pos, ghost.direction)


__all__ = [
    "PacmanEnvironment",
    "PacmanLayout",
    "PacmanState",
    "GhostState",
    "PacmanProblem",
    "Point",
]
