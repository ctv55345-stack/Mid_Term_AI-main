import pygame
import sys
import os
import threading
from typing import List, Optional, Tuple
from pathlib import Path
from queue import Queue

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from pacman.environment import PacmanEnvironment, PacmanProblem, PacmanState
from pacman.auto import run_auto_mode, _select_heuristic
from puzzle import AStar

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
PURPLE = (128, 0, 128)
LIGHT_GREEN = (144, 238, 144)
DARK_GRAY = (30, 30, 30)
CYAN = (0, 255, 255)

# Maximum screen size
MAX_SCREEN_WIDTH = 1800
MAX_SCREEN_HEIGHT = 1100
INFO_HEIGHT = 260
BUTTON_HEIGHT = 40

class PacmanGUI:
    def __init__(self, layout_path: Optional[Path] = None):
        pygame.init()
        
        # Load layout
        if layout_path and layout_path.exists():
            with open(layout_path, 'r', encoding='utf-8') as f:
                self.layout_lines = [line.rstrip('\n') for line in f]
        else:
            # Default layout
            self.layout_lines = [
                "%%%%%%%%%%",
                "%P....  E%",
                "% %% %%% %",
                "%..G  O  %",
                "%%%%%%%%%%"
            ]
        
        # Initialize environment
        self.env = PacmanEnvironment(self.layout_lines)
        self.problem = PacmanProblem(self.env)
        self.current_state = self.env.initial_state
        
        # Calculate max size of all rotations
        self.max_width = max(layout.width for layout in self.env.layouts)
        self.max_height = max(layout.height for layout in self.env.layouts)
        
        # Auto-scale CELL_SIZE to fit screen
        self.cell_size = self._calculate_optimal_cell_size()
        
        self.screen_width = self.max_width * self.cell_size
        self.screen_height = self.max_height * self.cell_size + INFO_HEIGHT
        
        # Ensure not exceeding screen limits
        if self.screen_width > MAX_SCREEN_WIDTH:
            self.screen_width = MAX_SCREEN_WIDTH
        if self.screen_height > MAX_SCREEN_HEIGHT:
            self.screen_height = MAX_SCREEN_HEIGHT
        
        # Minimum screen size
        self.screen_width = max(800, self.screen_width)
        self.screen_height = max(600, self.screen_height)
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Pacman AI Solver - Manual & Auto Mode")
        
        self.clock = pygame.time.Clock()
        
        # Font sizes
        font_size = max(20, min(28, self.cell_size // 2 + 4))
        small_font_size = max(16, min(22, self.cell_size // 2))
        self.font = pygame.font.Font(None, font_size)
        self.small_font = pygame.font.Font(None, small_font_size)
        
        # Pacman direction tracking
        self.pacman_direction = "right"
        
        # Load images
        self._load_images()
        
        # AI state
        self.path = []
        self.path_index = 0
        self.is_solving = False
        self.is_auto_play = False
        self.solving_thread = None
        self.solution_queue = Queue()
        self.is_computing = False
        self.auto_step_counter = 0
        self.message = ""
        self.message_color = WHITE
        self.message_timer = 0
        
        # Manual mode - ghost movement independent
        self.is_manual_mode = False
        self.manual_step_delay = 15  # Every 15 frames = 1 time step
        self.manual_frame_counter = 0  # Frame counter
        
        # Game over state
        self.is_game_over = False
        self.game_over_timer = 0
        
        # Rotation tracking
        self.last_layout_index = 0
        self.rotation_flash = 0
        
        # Power-up effects
        self.pie_flash = 0
        self.last_pie_timer = 0
        self.glow_pulse = 0
        
        self.stats = {
            'cost': 0,
            'expanded': 0,
            'frontier': 0,
            'current_step': 0
        }
        
        # Heuristics
        self.heuristics = [
            ("Auto", "auto"),
            ("ExactMST (H1)", "exact-mst"),
            ("Combined", "combo"),
            ("ExactDist", "exact-dist"),
            ("FoodMST", "mst"),
            ("PieAware", "pie")
        ]
        self.current_heuristic_idx = 0
        
        # Buttons
        self.buttons = self._create_buttons()
        
        print(f"Screen: {self.screen_width}x{self.screen_height}, Cell: {self.cell_size}, Maze: {self.max_width}x{self.max_height}")
    
    def _calculate_optimal_cell_size(self):
        """Calculate optimal CELL_SIZE"""
        max_cell_width = (MAX_SCREEN_WIDTH - 20) // self.max_width
        max_cell_height = (MAX_SCREEN_HEIGHT - INFO_HEIGHT - 20) // self.max_height
        
        optimal_size = min(max_cell_width, max_cell_height)
        
        if self.max_width <= 20 and self.max_height <= 20:
            return max(25, min(50, optimal_size))
        elif self.max_width <= 40 and self.max_height <= 40:
            return max(20, min(35, optimal_size))
        else:
            return max(15, min(25, optimal_size))
    
    def _load_images(self):
        """Load and scale images from pacman-art"""
        base_path = Path(__file__).parent / "pacman-art"
        
        # Load Pacman in 4 directions
        self.pacman_images = {}
        directions = ["up", "down", "left", "right"]
        
        for direction in directions:
            dir_path = base_path / f"pacman-{direction}"
            try:
                image_files = list(dir_path.glob("*.png"))
                if image_files:
                    img = pygame.image.load(str(image_files[0]))
                    img = pygame.transform.scale(img, (self.cell_size - 4, self.cell_size - 4))
                    self.pacman_images[direction] = img
                else:
                    self.pacman_images[direction] = None
            except Exception as e:
                print(f"Cannot load pacman-{direction}: {e}")
                self.pacman_images[direction] = None
        
        # Load Ghosts
        ghost_path = base_path / "ghosts"
        self.ghost_images = []
        
        try:
            ghost_files = sorted(list(ghost_path.glob("*.png")))
            for i in range(min(4, len(ghost_files))):
                img = pygame.image.load(str(ghost_files[i]))
                img = pygame.transform.scale(img, (self.cell_size - 6, self.cell_size - 6))
                self.ghost_images.append(img)
        except Exception as e:
            print(f"Cannot load ghosts: {e}")
            self.ghost_images = []
        
        while len(self.ghost_images) < 4:
            self.ghost_images.append(None)
        
        # Load power-up (strawberry)
        try:
            self.powerup_img = pygame.image.load(str(base_path / "other" / "strawberry.png"))
            self.powerup_img = pygame.transform.scale(self.powerup_img, (self.cell_size - 8, self.cell_size - 8))
        except Exception as e:
            print(f"Cannot load strawberry.png: {e}")
            self.powerup_img = None
        
        # Load scared ghost (apple)
        try:
            self.scared_ghost_img = pygame.image.load(str(base_path / "other" / "apple.png"))
            self.scared_ghost_img = pygame.transform.scale(self.scared_ghost_img, (self.cell_size - 6, self.cell_size - 6))
        except Exception as e:
            print(f"Cannot load apple.png: {e}")
            self.scared_ghost_img = None
        
        # Load teleport icon
        self._load_teleport_icon()
    
    def _load_teleport_icon(self):
        """Load or create teleport icon"""
        try:
            # Try to load from file
            base_path = Path(__file__).parent / "pacman-art" / "other"
            teleport_path = base_path / "teleport.png"
            
            if teleport_path.exists():
                img = pygame.image.load(str(teleport_path))
                self.teleport_icon = pygame.transform.scale(img, (self.cell_size - 8, self.cell_size - 8))
            else:
                self.teleport_icon = None
        except:
            self.teleport_icon = None
    
    def _draw_teleport_indicator(self, surface: pygame.Surface, rect: pygame.Rect, is_current: bool = False):
        """
        Draw teleport indicator
        - surface: where to draw
        - rect: cell position
        - is_current: whether Pacman is currently here
        """
        
        if self.teleport_icon:
            # Use icon if available
            icon_rect = self.teleport_icon.get_rect(center=rect.center)
            surface.blit(self.teleport_icon, icon_rect)
        else:
            # Draw manually if no icon
            center_x, center_y = rect.center
            
            # Draw outer circle (portal effect)
            radius_outer = max(8, self.cell_size // 3)
            radius_inner = max(5, self.cell_size // 4)
            
            if is_current:
                # Pacman is here - strong highlight
                pygame.draw.circle(surface, CYAN, rect.center, radius_outer, 3)
                pygame.draw.circle(surface, YELLOW, rect.center, radius_inner)
                
                # Draw large T
                font_size = max(16, self.cell_size // 2)
                t_font = pygame.font.Font(None, font_size)
                t_text = t_font.render("T", True, WHITE)
                t_rect = t_text.get_rect(center=rect.center)
                surface.blit(t_text, t_rect)
            else:
                # Normal teleport point
                # Draw 2 concentric circles (portal effect)
                pygame.draw.circle(surface, CYAN, rect.center, radius_outer, 2)
                pygame.draw.circle(surface, (0, 200, 200), rect.center, radius_inner, 2)
                
                # Draw small T
                font_size = max(12, self.cell_size // 3)
                t_font = pygame.font.Font(None, font_size)
                t_text = t_font.render("T", True, CYAN)
                t_rect = t_text.get_rect(center=rect.center)
                surface.blit(t_text, t_rect)
    
    def _handle_game_over(self):
        """Handle game over - show message and reset"""
        self.is_game_over = True
        self.game_over_timer = 180  # 6 seconds (180 frames)
        self.is_manual_mode = False
        self.is_auto_play = False
        self.show_message("GAME OVER! Ghost caught you!", RED, 180)
        print("GAME OVER - Ghost caught Pacman!")
    
    def _check_game_over(self):
        """Check game over and handle"""
        if self.is_game_over:
            self.game_over_timer -= 1
            if self.game_over_timer <= 0:
                # Reset game after showing message
                self.reset()
                self.show_message("Game reset! Try again!", YELLOW, 90)
        
    def _create_buttons(self):
        """Create buttons with dynamic positioning"""
        maze_height = self.max_height * self.cell_size
        y_start = maze_height + 10
        
        button_width = max(120, min(150, self.screen_width // 10))
        spacing = max(8, min(15, self.screen_width // 80))
        
        buttons = [
            {"rect": pygame.Rect(10, y_start, button_width, BUTTON_HEIGHT), 
             "text": "Solve", "action": "solve"},
            {"rect": pygame.Rect(10 + button_width + spacing, y_start, button_width, BUTTON_HEIGHT),
             "text": "Auto Play", "action": "auto"},
            {"rect": pygame.Rect(10 + 2*(button_width + spacing), y_start, button_width, BUTTON_HEIGHT),
             "text": "Step", "action": "step"},
            {"rect": pygame.Rect(10 + 3*(button_width + spacing), y_start, button_width, BUTTON_HEIGHT),
             "text": "Reset", "action": "reset"},
            {"rect": pygame.Rect(10 + 4*(button_width + spacing), y_start, button_width, BUTTON_HEIGHT),
             "text": "Manual", "action": "manual"},
            {"rect": pygame.Rect(10, y_start + BUTTON_HEIGHT + spacing, button_width*2 + spacing, BUTTON_HEIGHT),
             "text": f"H: {self.heuristics[self.current_heuristic_idx][0]}", "action": "change_h"}
        ]
        return buttons
    
    def draw_grid(self):
        layout = self.env.layouts[self.current_state.layout_index]
        
        current_height = layout.height
        current_width = layout.width
        
        # Calculate offset to center maze
        maze_width = current_width * self.cell_size
        maze_height = current_height * self.cell_size
        
        offset_x = (self.screen_width - maze_width) // 2
        offset_y = (self.max_height * self.cell_size - maze_height) // 2
        
        # Detect rotation
        if self.current_state.layout_index != self.last_layout_index:
            self.rotation_flash = 30
            self.show_message(f"Maze rotated {self.current_state.layout_index * 90}°", ORANGE, 90)
            self.last_layout_index = self.current_state.layout_index
        
        flash_overlay = self.rotation_flash > 0
        if flash_overlay:
            self.rotation_flash -= 1
        
        # Detect when just ate pie
        if self.current_state.pie_timer > self.last_pie_timer:
            self.pie_flash = 20
            self.show_message("POWER UP!", YELLOW, 60)
        
        self.last_pie_timer = self.current_state.pie_timer
        
        # Draw background
        is_goal = self.problem.is_goal(self.current_state)
        if is_goal:
            self.screen.fill((20, 40, 20))
        else:
            self.screen.fill(DARK_GRAY)
        
        # Flash effect when ate pie
        if self.pie_flash > 0:
            flash_surface = pygame.Surface((self.screen_width, self.screen_height))
            flash_surface.fill(YELLOW)
            alpha = int((self.pie_flash / 20) * 60)
            flash_surface.set_alpha(alpha)
            self.screen.blit(flash_surface, (0, 0))
            self.pie_flash -= 1
        
        # Draw background for maze area
        maze_rect = pygame.Rect(offset_x, offset_y, maze_width, maze_height)
        pygame.draw.rect(self.screen, BLACK, maze_rect)
        
        # Draw maze with offset
        for row in range(current_height):
            for col in range(current_width):
                pos = (row, col)
                rect = pygame.Rect(
                    col * self.cell_size + offset_x, 
                    row * self.cell_size + offset_y, 
                    self.cell_size, 
                    self.cell_size
                )
                
                # Draw floor
                if layout.is_wall(pos):
                    color = BLUE
                    if flash_overlay:
                        color = tuple(min(c + 50, 255) for c in color)
                    pygame.draw.rect(self.screen, color, rect)
                else:
                    if is_goal:
                        pygame.draw.rect(self.screen, (10, 30, 10), rect)
                    else:
                        pygame.draw.rect(self.screen, BLACK, rect)
                
                # Draw exit gate
                if pos == layout.exit_gate:
                    color = LIGHT_GREEN if is_goal else GREEN
                    pygame.draw.rect(self.screen, color, rect.inflate(-10, -10))
                
                # Draw food
                if pos in self.current_state.food:
                    dot_size = max(4, self.cell_size // 7)
                    pygame.draw.circle(self.screen, WHITE, rect.center, dot_size)
                
                # Draw pie
                if pos in self.current_state.pies:
                    if self.powerup_img:
                        img_rect = self.powerup_img.get_rect(center=rect.center)
                        self.screen.blit(self.powerup_img, img_rect)
                    else:
                        pie_size = max(8, self.cell_size // 3)
                        pygame.draw.circle(self.screen, ORANGE, rect.center, pie_size)
                
                # Grid lines
                pygame.draw.rect(self.screen, GRAY, rect, 1)
        
        # Draw teleport indicators - before drawing ghosts/pacman
        for corner_name, corner_pos in layout.teleports.items():
            row, col = corner_pos
            rect = pygame.Rect(
                col * self.cell_size + offset_x,
                row * self.cell_size + offset_y,
                self.cell_size,
                self.cell_size
            )
            
            # Check if Pacman is currently here
            is_current = (self.current_state.pacman_pos == corner_pos)
            
            # Draw indicator
            self._draw_teleport_indicator(self.screen, rect, is_current)
        
        # Draw ghosts
        has_pie_timer = self.current_state.pie_timer > 0
        for i, ghost in enumerate(self.current_state.ghosts):
            row, col = ghost.position
            rect = pygame.Rect(
                col * self.cell_size + offset_x,
                row * self.cell_size + offset_y,
                self.cell_size,
                self.cell_size
            )
            
            if has_pie_timer:
                if self.current_state.pie_timer <= 2:
                    if pygame.time.get_ticks() % 400 < 200:
                        if self.scared_ghost_img:
                            img_rect = self.scared_ghost_img.get_rect(center=rect.center)
                            self.screen.blit(self.scared_ghost_img, img_rect)
                        else:
                            ghost_size = max(10, self.cell_size // 3)
                            pygame.draw.circle(self.screen, BLUE, rect.center, ghost_size)
                    else:
                        if self.ghost_images and i < len(self.ghost_images) and self.ghost_images[i]:
                            img_rect = self.ghost_images[i].get_rect(center=rect.center)
                            img_alpha = self.ghost_images[i].copy()
                            img_alpha.set_alpha(128)
                            self.screen.blit(img_alpha, img_rect)
                        else:
                            ghost_size = max(10, self.cell_size // 3)
                            pygame.draw.circle(self.screen, RED, rect.center, ghost_size)
                else:
                    if self.scared_ghost_img:
                        img_rect = self.scared_ghost_img.get_rect(center=rect.center)
                        self.screen.blit(self.scared_ghost_img, img_rect)
                    else:
                        ghost_size = max(10, self.cell_size // 3)
                        pygame.draw.circle(self.screen, BLUE, rect.center, ghost_size)
            else:
                if self.ghost_images and i < len(self.ghost_images) and self.ghost_images[i]:
                    img_rect = self.ghost_images[i].get_rect(center=rect.center)
                    self.screen.blit(self.ghost_images[i], img_rect)
                else:
                    ghost_size = max(10, self.cell_size // 3)
                    pygame.draw.circle(self.screen, RED, rect.center, ghost_size)
        
        # Draw Pacman with glow effect when powered
        pacman_row, pacman_col = self.current_state.pacman_pos
        pacman_rect = pygame.Rect(
            pacman_col * self.cell_size + offset_x,
            pacman_row * self.cell_size + offset_y,
            self.cell_size,
            self.cell_size
        )
        
        # Power-up glow effect
        if self.current_state.pie_timer > 0:
            self.glow_pulse += 0.15
            
            base_glow = max(14, self.cell_size // 2 + 2)
            pulse_size = base_glow + int(4 * abs(pygame.math.Vector2(1, 0).rotate(self.glow_pulse * 180 / 3.14159).x))
            
            if self.current_state.pie_timer <= 2:
                if pygame.time.get_ticks() % 400 < 200:
                    glow_color = ORANGE
                else:
                    glow_color = YELLOW
            else:
                glow_color = YELLOW
            
            for i in range(3):
                radius = pulse_size + i * 3
                alpha_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                glow_alpha = max(0, 100 - i * 30)
                pygame.draw.circle(alpha_surface, (*glow_color, glow_alpha), (radius, radius), radius)
                glow_rect = alpha_surface.get_rect(center=pacman_rect.center)
                self.screen.blit(alpha_surface, glow_rect)
        else:
            self.glow_pulse = 0
        
        # Draw Pacman sprite
        pacman_img = self.pacman_images.get(self.pacman_direction)
        if pacman_img:
            img_rect = pacman_img.get_rect(center=pacman_rect.center)
            self.screen.blit(pacman_img, img_rect)
        else:
            pacman_size = max(12, self.cell_size // 2)
            pygame.draw.circle(self.screen, YELLOW, pacman_rect.center, pacman_size)
        
        # Draw border for maze
        pygame.draw.rect(self.screen, WHITE, maze_rect, 2)
        
        # Legend - show teleport instructions
        if len(layout.teleports) > 0:
            legend_y = 10
            if self.rotation_flash > 0:
                legend_y += 30
            if self.current_state.pie_timer > 0:
                legend_y += 30
            
            # Show legend
            legend_text = self.small_font.render(
                f"Blue = Teleport ({len(layout.teleports)} points)", 
                True, 
                CYAN
            )
            legend_rect = legend_text.get_rect()
            legend_rect.topright = (self.screen_width - 10, legend_y)
            self.screen.blit(legend_text, legend_rect)
        
        # Rotation indicator
        if self.rotation_flash > 0:
            rotation_text = self.font.render("ROTATING", True, ORANGE)
            text_rect = rotation_text.get_rect()
            text_rect.topright = (self.screen_width - 10, 10)
            self.screen.blit(rotation_text, text_rect)
        
        # Power-up indicator
        if self.current_state.pie_timer > 0:
            power_text = self.font.render(f"POWER: {self.current_state.pie_timer}", True, YELLOW)
            text_rect = power_text.get_rect()
            text_rect.topleft = (10, 10)
            self.screen.blit(power_text, text_rect)
        
        # Manual mode indicator
        if self.is_manual_mode:
            mode_text = self.font.render("MANUAL MODE", True, CYAN)
            text_rect = mode_text.get_rect()
            text_rect.midtop = (self.screen_width // 2, 10)
            self.screen.blit(mode_text, text_rect)
            
            controls_text = self.small_font.render("↑↓←→/WASD: Move | T: Teleport | Space: Stop | ESC: Exit", True, WHITE)
            controls_rect = controls_text.get_rect()
            controls_rect.midtop = (self.screen_width // 2, 35)
            self.screen.blit(controls_text, controls_rect)
    
    def draw_info(self):
        """Draw info panel with responsive layout - 3 COLUMNS"""
        maze_height = self.max_height * self.cell_size
        y_offset = maze_height + 10
        
        # Draw buttons
        for btn in self.buttons:
            if btn["action"] == "auto" and self.is_auto_play:
                color = PURPLE
            elif btn["action"] == "manual" and self.is_manual_mode:
                color = CYAN
            elif self.is_computing and btn["action"] == "solve":
                color = ORANGE
            else:
                color = WHITE
            
            pygame.draw.rect(self.screen, color, btn["rect"])
            pygame.draw.rect(self.screen, BLACK, btn["rect"], 2)
            
            text = self.font.render(btn["text"], True, BLACK)
            text_rect = text.get_rect(center=btn["rect"].center)
            self.screen.blit(text, text_rect)
        
        # Display message
        if self.message and self.message_timer > 0:
            msg_surface = self.font.render(self.message, True, self.message_color)
            self.screen.blit(msg_surface, (10, y_offset - 35))
            self.message_timer -= 1
        
        # Stats - divided into 3 columns
        stats_y = y_offset + 2*BUTTON_HEIGHT + 20
        
        is_goal = self.problem.is_goal(self.current_state)
        
        # Column 1 - Game Progress
        col1_x = 10
        stats_col1 = []
        
        if self.is_game_over:
            stats_col1.append(("GAME OVER!", RED))
        elif is_goal:
            stats_col1.append(("GOAL REACHED!", LIGHT_GREEN))
        
        if not self.is_game_over:
            mode_text = "Manual" if self.is_manual_mode else "AI"
            mode_color = CYAN if self.is_manual_mode else WHITE
            stats_col1.append((f"Mode: {mode_text}", mode_color))
        
        stats_col1.extend([
            (f"Cost: {self.stats['cost']}", WHITE),
            (f"Expanded: {self.stats['expanded']}", WHITE),
            (f"Frontier: {self.stats['frontier']}", WHITE),
            (f"Step: {self.stats['current_step']}/{len(self.path)}", WHITE),
        ])
        
        # Column 2 - Game State
        col2_x = self.screen_width // 3
        stats_col2 = [
            (f"Food left: {len(self.current_state.food)}", WHITE),
        ]
        
        pie_color = WHITE
        if self.current_state.pie_timer > 0:
            pie_color = ORANGE if self.current_state.pie_timer <= 2 else YELLOW
        stats_col2.append((f"Power: {self.current_state.pie_timer}", pie_color))
        
        # Use real time_step (both modes)
        time_color = CYAN if self.is_manual_mode else WHITE
        stats_col2.append((f"Time: {self.current_state.time_step}", time_color))
        
        # Teleport info - more details
        layout = self.env.layouts[self.current_state.layout_index]
        
        if len(layout.teleports) > 0:
            # Check if at teleport point
            corner = layout.corner_name(self.current_state.pacman_pos)
            
            if corner:
                # Currently at teleport point
                # Count number of destinations
                num_destinations = len(layout.teleports) - 1
                
                if self.is_manual_mode:
                    stats_col2.append((f"At {corner} - Press T ({num_destinations} dest)", CYAN))
                else:
                    stats_col2.append((f"At {corner} - Can teleport", CYAN))
            else:
                # Not at teleport point
                # Find nearest teleport
                min_dist = float('inf')
                nearest_corner = None
                
                for name, pos in layout.teleports.items():
                    dist = abs(pos[0] - self.current_state.pacman_pos[0]) + abs(pos[1] - self.current_state.pacman_pos[1])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_corner = name
                
                if nearest_corner and self.is_manual_mode:
                    stats_col2.append((f"Nearest: {nearest_corner} ({min_dist} steps)", GRAY))
        else:
            stats_col2.append((f"No teleport available", GRAY))
        
        # Column 3 - Maze Info
        col3_x = 2 * self.screen_width // 3
        layout = self.env.layouts[self.current_state.layout_index]
        
        # Rotation based on real time_step
        next_rotation = 30 - (self.current_state.time_step % 30)
        rotation_color = ORANGE if next_rotation <= 5 else WHITE
        
        stats_col3 = [
            (f"Maze: {layout.height}x{layout.width}", WHITE),
            (f"Cell: {self.cell_size}px", WHITE),
            (f"Rotation: {self.current_state.layout_index}/3", WHITE),
            (f"Next rotate: {next_rotation} steps", rotation_color),  # "steps" instead of "frames"
        ]
        
        # Draw all columns
        for i, (text, color) in enumerate(stats_col1):
            surface = self.small_font.render(text, True, color)
            self.screen.blit(surface, (col1_x, stats_y + i*22))
        
        for i, (text, color) in enumerate(stats_col2):
            surface = self.small_font.render(text, True, color)
            self.screen.blit(surface, (col2_x, stats_y + i*22))
        
        for i, (text, color) in enumerate(stats_col3):
            surface = self.small_font.render(text, True, color)
            self.screen.blit(surface, (col3_x, stats_y + i*22))
    
    def show_message(self, msg: str, color=WHITE, duration=90):
        """Display temporary message"""
        self.message = msg
        self.message_color = color
        self.message_timer = duration
    
    def _update_pacman_direction(self, action_name: str):
        """Update Pacman's direction based on action"""
        direction_map = {
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right"
        }
        if action_name in direction_map:
            self.pacman_direction = direction_map[action_name]
    
    def handle_click(self, pos):
        if self.is_computing:
            self.show_message("⏳ Computing...", ORANGE, 30)
            return
        
        for btn in self.buttons:
            if btn["rect"].collidepoint(pos):
                action = btn["action"]
                
                if action == "solve":
                    self.solve_puzzle()
                elif action == "auto":
                    self.toggle_auto_play()
                elif action == "step":
                    self.step_forward()
                elif action == "reset":
                    self.reset()
                elif action == "manual":
                    self.toggle_manual_mode()
                elif action == "change_h":
                    self.change_heuristic()
    
    def toggle_manual_mode(self):
        """Toggle between manual and AI mode"""
        self.is_manual_mode = not self.is_manual_mode
        
        if self.is_manual_mode:
            self.is_auto_play = False
            self.manual_frame_counter = 0
            self.show_message("Manual Mode ON - Use Arrow Keys!", CYAN, 120)
        else:
            self.show_message("Manual Mode OFF - AI Mode Active", WHITE, 90)
    
    def handle_keyboard(self, key):
        """Handle keyboard input for manual mode - PACMAN ONLY"""
        if not self.is_manual_mode:
            return
        
        # Check game over
        if self.is_game_over:
            return
        
        # ESC - Exit manual mode
        if key == pygame.K_ESCAPE:
            self.toggle_manual_mode()
            return
        
        # Check goal
        if self.problem.is_goal(self.current_state):
            self.show_message("Already at goal!", LIGHT_GREEN, 60)
            return
        
        # T - TELEPORT (FIXED)
        if key == pygame.K_t:
            self._handle_teleport_manual()
            return
        
        # Map keyboard to actions
        key_to_action = {
            pygame.K_UP: "Up",
            pygame.K_DOWN: "Down",
            pygame.K_LEFT: "Left",
            pygame.K_RIGHT: "Right",
            pygame.K_w: "Up",
            pygame.K_s: "Down",
            pygame.K_a: "Left",
            pygame.K_d: "Right",
            pygame.K_SPACE: "Stop"
        }
        
        action_name = key_to_action.get(key)
        if not action_name:
            return
        
        # Update Pacman direction
        self._update_pacman_direction(action_name)
        
        # Move Pacman only - no ghost movement here
        layout = self.env.layouts[self.current_state.layout_index]
        
        delta_map = {
            "Up": (-1, 0),
            "Down": (1, 0),
            "Left": (0, -1),
            "Right": (0, 1),
            "Stop": (0, 0)
        }
        
        delta = delta_map[action_name]
        dr, dc = delta
        new_pos = (self.current_state.pacman_pos[0] + dr, self.current_state.pacman_pos[1] + dc)
        
        # Check 1: In bounds
        if not layout.in_bounds(new_pos):
            self.show_message("Out of bounds!", RED, 30)
            return
        
        # Check 2: Wall (with pie phasing)
        if layout.is_wall(new_pos) and self.current_state.pie_timer <= 0:
            self.show_message("Wall!", RED, 30)
            return
        
        # Check 3: Ghost collision (current ghosts)
        if any(g.position == new_pos for g in self.current_state.ghosts):
            self.show_message("Ghost blocking!", RED, 30)
            return
        
        # Update state - Pacman moved
        from pacman.environment import PacmanState
        
        # Update pie timer
        pie_timer = max(self.current_state.pie_timer - 1, 0) if action_name != "Stop" else self.current_state.pie_timer
        
        # Eat pie
        new_pies = set(self.current_state.pies)
        if new_pos in new_pies:
            new_pies.remove(new_pos)
            pie_timer = 5
            self.show_message("Power Up!", YELLOW, 60)
        
        # Eat food
        new_food = set(self.current_state.food)
        if new_pos in new_food:
            new_food.remove(new_pos)
        
        # Ghosts stay same (they move independently)
        new_ghosts = self.current_state.ghosts
        
        # Check: Still safe after move?
        if any(g.position == new_pos for g in new_ghosts):
            self.show_message("Ghost caught you!", RED, 60)
            return
        
        # Increment time_step - only when Pacman moves
        new_time_step = self.current_state.time_step + 1
        
        # Create new state
        new_state = PacmanState(
            pacman_pos=new_pos,
            ghosts=new_ghosts,
            food=frozenset(new_food),
            pies=frozenset(new_pies),
            layout_index=self.current_state.layout_index,
            time_step=new_time_step,  # Incremented
            pie_timer=pie_timer
        )
        
        # Check rotation - based on time_step
        if new_time_step % 30 == 0:
            print(f"Rotation at time_step {new_time_step}")
            new_state = self.env.rotate_state(new_state)
            self.show_message(f"Maze rotated! (step {new_time_step})", ORANGE, 90)
        
        self.current_state = new_state
        self.stats['current_step'] += 1
        self.stats['cost'] += 1
        
        # Check win
        if self.problem.is_goal(self.current_state):
            self.show_message("YOU WON! Goal reached!", LIGHT_GREEN, 180)
    
    def _handle_teleport_manual(self):
        """Handle teleport in manual mode - IMPROVED VERSION"""
        layout = self.env.layouts[self.current_state.layout_index]
        current_pos = self.current_state.pacman_pos
        
        # Check: At any corner?
        corner = layout.corner_name(current_pos)
        
        if not corner:
            # Show where teleport points are
            if len(layout.teleports) == 0:
                self.show_message("No teleport points on this map!", ORANGE, 90)
            else:
                teleport_names = list(layout.teleports.keys())
                self.show_message(f"Not at teleport! Available: {', '.join(teleport_names)}", ORANGE, 90)
            return
        
        # Get available destinations
        available_corners = [
            (name, pos) for name, pos in layout.teleports.items()
            if pos != current_pos
        ]
        
        if not available_corners:
            self.show_message("No other teleport destinations!", RED, 60)
            return
        
        # Cycle through corners intelligently
        # Find next corner in clockwise order
        corner_order = ["TL", "TR", "BR", "BL"]
        
        try:
            current_idx = corner_order.index(corner)
            
            # Try to find next valid corner in order
            for i in range(1, 5):
                check_idx = (current_idx + i) % 4
                check_name = corner_order[check_idx]
                
                if check_name in layout.teleports and check_name != corner:
                    target_name = check_name
                    target_pos = layout.teleports[check_name]
                    break
            else:
                # Fallback
                target_name, target_pos = available_corners[0]
        except:
            # Fallback
            target_name, target_pos = available_corners[0]
        
        # Check ghost at target
        if any(g.position == target_pos for g in self.current_state.ghosts):
            self.show_message(f"Ghost at {target_name}!", RED, 60)
            return
        
        from pacman.environment import PacmanState
        
        # Update pie timer
        pie_timer = max(self.current_state.pie_timer - 1, 0)
        
        # Eat pie at target
        new_pies = set(self.current_state.pies)
        if target_pos in new_pies:
            new_pies.remove(target_pos)
            pie_timer = 5
            self.show_message("Power Up at teleport!", YELLOW, 60)
        
        # Eat food at target
        new_food = set(self.current_state.food)
        if target_pos in new_food:
            new_food.remove(target_pos)
        
        # Ghosts don't move during teleport (instant)
        new_ghosts = self.current_state.ghosts
        
        # Double check ghost
        if any(g.position == target_pos for g in new_ghosts):
            self.show_message("Ghost at destination!", RED, 60)
            return
        
        # Increment time_step - teleport = 1 step
        new_time_step = self.current_state.time_step + 1
        
        # Create new state
        new_state = PacmanState(
            pacman_pos=target_pos,
            ghosts=new_ghosts,
            food=frozenset(new_food),
            pies=frozenset(new_pies),
            layout_index=self.current_state.layout_index,
            time_step=new_time_step,  # Incremented
            pie_timer=pie_timer
        )
        
        # Check rotation
        if new_time_step % 30 == 0:
            print(f"Rotation at time_step {new_time_step}")
            new_state = self.env.rotate_state(new_state)
            self.show_message(f"Maze rotated! (step {new_time_step})", ORANGE, 90)
        
        self.current_state = new_state
        self.stats['current_step'] += 1
        self.stats['cost'] += 1
        
        # Show success with arrow
        self.show_message(f"Teleported {corner} -> {target_name}!", CYAN, 90)
        
        # Check win
        if self.problem.is_goal(self.current_state):
            self.show_message("YOU WON! Goal reached!", LIGHT_GREEN, 180)
    
    def update_manual_mode(self):
        """
        Only move ghosts - do not increment time
        - Ghosts move independently
        - Do NOT affect time_step
        - Do NOT trigger rotation
        """
        if not self.is_manual_mode:
            return
        
        if self.is_game_over:
            return
        
        if self.problem.is_goal(self.current_state):
            return
        
        self.manual_frame_counter += 1
        
        # Move ghosts every N frames
        if self.manual_frame_counter >= self.manual_step_delay:
            self.manual_frame_counter = 0
            # Removed: self.manual_time_step += 1
            
            from pacman.environment import PacmanState
            layout = self.env.layouts[self.current_state.layout_index]
            
            # Move ghosts
            new_ghosts = tuple(self.problem._move_ghost(g, layout) for g in self.current_state.ghosts)
            
            # Check if ghost catches Pacman
            if any(g.position == self.current_state.pacman_pos for g in new_ghosts):
                self._handle_game_over()
                return
            
            # Update state - only ghosts, do not increment time
            new_state = PacmanState(
                pacman_pos=self.current_state.pacman_pos,
                ghosts=new_ghosts,
                food=self.current_state.food,
                pies=self.current_state.pies,
                layout_index=self.current_state.layout_index,
                time_step=self.current_state.time_step,  # Not incremented
                pie_timer=self.current_state.pie_timer
            )
            
            # Removed: Rotation check here
            
            self.current_state = new_state
    
    def solve_puzzle(self):
        if self.is_computing:
            self.show_message("⏳ Computing...", ORANGE, 30)
            return
        
        if self.is_manual_mode:
            self.show_message("Exit Manual Mode first!", ORANGE, 60)
            return
        
        while not self.solution_queue.empty():
            self.solution_queue.get()
        
        heuristic_name = self.heuristics[self.current_heuristic_idx][1]
        print(f"🔍 Solving with {heuristic_name}...")
        self.show_message(f"🔍 Solving with {heuristic_name}...", ORANGE, 90)
        
        self.is_computing = True
        
        def solve_worker():
            try:
                path, cost, expanded, frontier = run_auto_mode(
                    self.layout_lines, 
                    heuristic=heuristic_name
                )
                self.solution_queue.put({
                    'success': True,
                    'path': path if path is not None else [],
                    'cost': cost,
                    'expanded': expanded,
                    'frontier': frontier
                })
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                self.solution_queue.put({'success': False, 'error': str(e)})
        
        self.solving_thread = threading.Thread(target=solve_worker, daemon=True)
        self.solving_thread.start()
    
    def toggle_auto_play(self):
        if self.is_manual_mode:
            self.show_message("Exit Manual Mode first!", ORANGE, 60)
            return
        
        if not self.is_solving:
            self.show_message("No solution! Solve first.", RED, 90)
            return
        
        if self.path_index >= len(self.path):
            self.show_message("Already completed!", GREEN, 60)
            return
        
        self.is_auto_play = not self.is_auto_play
        
        if self.is_auto_play:
            self.show_message("Auto play ON", GREEN, 60)
            self.auto_step_counter = 0
        else:
            self.show_message("Auto play OFF", YELLOW, 60)
    
    def step_forward(self):
        if self.is_computing:
            return
        
        if self.is_manual_mode:
            self.show_message("Exit Manual Mode first!", ORANGE, 60)
            return
        
        if not self.is_solving:
            self.show_message("No solution! Solve first.", RED, 90)
            return
        
        if self.problem.is_goal(self.current_state):
            self.is_auto_play = False
            self.show_message("Goal reached!", LIGHT_GREEN, 120)
            return
        
        if self.path_index >= len(self.path):
            self.is_auto_play = False
            self.show_message("Path completed!", GREEN, 90)
            return
        
        action = self.path[self.path_index]
        action_name = action.type
        success = False
        
        delta_map = {
            "Up": (-1, 0),
            "Down": (1, 0),
            "Left": (0, -1),
            "Right": (0, 1),
            "Stop": (0, 0)
        }
        
        if action_name in delta_map:
            self._update_pacman_direction(action_name)
            
            delta = delta_map[action_name]
            move_result = self.problem._apply_move(
                self.current_state,
                self.env.layouts[self.current_state.layout_index],
                action_name,
                delta
            )
            if move_result:
                self.current_state, _, _ = move_result[0]
                success = True
        
        elif action_name == "Teleport":
            target = action.payload.get("to") if action.payload else None
            if target:
                teleport_result = self.problem._apply_teleport(
                    self.current_state,
                    self.env.layouts[self.current_state.layout_index],
                    target
                )
                if teleport_result:
                    self.current_state = teleport_result
                    success = True
        
        if success:
            self.path_index += 1
            self.stats['current_step'] = self.path_index
        else:
            print(f"Action {action_name} failed!")
            self.show_message(f"Action {action_name} failed!", RED, 90)
            self.is_auto_play = False
    
    def reset(self):
        self.current_state = self.env.initial_state
        self.path = []
        self.path_index = 0
        self.is_solving = False
        self.is_auto_play = False
        self.is_computing = False
        self.auto_step_counter = 0
        self.last_layout_index = 0
        self.rotation_flash = 0
        self.pacman_direction = "right"
        self.pie_flash = 0
        self.last_pie_timer = 0
        self.glow_pulse = 0
        self.is_manual_mode = False
        self.manual_frame_counter = 0  # Reset
        self.is_game_over = False  # Reset game over
        self.game_over_timer = 0  # Reset timer
        
        while not self.solution_queue.empty():
            self.solution_queue.get()
        
        self.stats = {
            'cost': 0,
            'expanded': 0,
            'frontier': 0,
            'current_step': 0
        }
        
        self.show_message("Reset complete!", YELLOW, 60)
    
    def change_heuristic(self):
        if self.is_computing:
            self.show_message("⏳ Wait for computation!", ORANGE, 60)
            return
        
        self.current_heuristic_idx = (self.current_heuristic_idx + 1) % len(self.heuristics)
        heuristic_name = self.heuristics[self.current_heuristic_idx][0]
        self.buttons[5]["text"] = f"H: {heuristic_name}"
        
        self.reset()
        self.show_message(f"🔧 Heuristic: {heuristic_name}", WHITE, 90)
    
    def check_solution_ready(self):
        """Check if there's a new solution from thread"""
        if not self.solution_queue.empty():
            result = self.solution_queue.get()
            self.is_computing = False
            
            if result['success']:
                self.path = result['path']
                self.stats['cost'] = result['cost']
                self.stats['expanded'] = result['expanded']
                self.stats['frontier'] = result['frontier']
                self.path_index = 0
                self.stats['current_step'] = 0
                self.is_solving = True
                
                print(f"Solution found! Length: {len(self.path)}")
                self.show_message(f"Solution found! Length: {len(self.path)}", GREEN, 120)
            else:
                self.path = []
                self.is_solving = False
                self.stats = {
                    'cost': 0,
                    'expanded': 0,
                    'frontier': 0,
                    'current_step': 0
                }
                error = result.get('error', 'Unknown error')
                print(f"Failed: {error}")
                self.show_message(f"Failed: {error[:30]}...", RED, 120)
    
    def run(self):
        running = True
        
        while running:
            self.check_solution_ready()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_keyboard(event.key)
            
            # Auto play (only when not in manual mode)
            if self.is_auto_play and not self.is_manual_mode:
                if self.path_index >= len(self.path):
                    self.is_auto_play = False
                    self.show_message("Auto play completed!", GREEN, 90)
                elif self.problem.is_goal(self.current_state):
                    self.is_auto_play = False
                    self.show_message("Goal reached!", LIGHT_GREEN, 120)
                else:
                    self.auto_step_counter += 1
                    if self.auto_step_counter >= 10:
                        self.step_forward()
                        self.auto_step_counter = 0
            
            # Auto-update ghosts in manual mode
            if self.is_manual_mode:
                self.update_manual_mode()
            
            # Check game over
            self._check_game_over()
            
            # Draw
            self.draw_grid()
            self.draw_info()
            pygame.display.flip()
            self.clock.tick(30)
        
        pygame.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, help="Path to layout file")
    args = parser.parse_args()
    
    gui = PacmanGUI(args.layout)
    gui.run()


if __name__ == "__main__":
    main()