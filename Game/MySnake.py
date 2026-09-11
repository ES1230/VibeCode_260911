"""Pygame Snake game."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pygame


CELL_SIZE = 24
GRID_COLUMNS = 25
GRID_ROWS = 22
BOARD_WIDTH = CELL_SIZE * GRID_COLUMNS
BOARD_HEIGHT = CELL_SIZE * GRID_ROWS
SIDE_WIDTH = 220
WINDOW_WIDTH = BOARD_WIDTH + SIDE_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT
FPS = 60
MOVE_INTERVAL = 115
HIGH_SCORE_FILE = Path(__file__).with_name("snake_high_score.json")

BACKGROUND = (10, 16, 30)
BOARD_BACKGROUND = (14, 24, 42)
GRID_COLOR = (24, 39, 62)
PANEL_BACKGROUND = (18, 29, 49)
TEXT = (231, 239, 248)
MUTED_TEXT = (145, 164, 187)
SNAKE_HEAD = (74, 222, 128)
SNAKE_BODY = (34, 197, 94)
FOOD = (251, 113, 133)
ACCENT = (45, 212, 191)


class SnakeGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Neon Snake")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = self.get_font(30, bold=True)
        self.heading_font = self.get_font(20, bold=True)
        self.body_font = self.get_font(16)
        self.small_font = self.get_font(13)
        self.running = True
        self.paused = False
        self.game_over = False
        self.move_timer = 0
        self.direction = (1, 0)
        self.next_direction = self.direction
        self.snake: list[tuple[int, int]] = []
        self.food = (0, 0)
        self.score = 0
        self.high_score = self.load_high_score()
        self.reset_game()

    @staticmethod
    def get_font(size: int, bold: bool = False) -> pygame.font.Font:
        candidates = ("malgungothic", "맑은 고딕", "segoeui", "arial")
        for name in candidates:
            font = pygame.font.SysFont(name, size, bold=bold)
            if font:
                return font
        return pygame.font.Font(None, size)

    def load_high_score(self) -> int:
        try:
            value = json.loads(HIGH_SCORE_FILE.read_text(encoding="utf-8"))
            return int(value) if isinstance(value, int) else 0
        except (OSError, ValueError, TypeError):
            return 0

    def save_high_score(self) -> None:
        try:
            HIGH_SCORE_FILE.write_text(str(self.high_score), encoding="utf-8")
        except OSError:
            pass

    def reset_game(self) -> None:
        center_x = GRID_COLUMNS // 2
        center_y = GRID_ROWS // 2
        self.snake = [
            (center_x, center_y),
            (center_x - 1, center_y),
            (center_x - 2, center_y),
        ]
        self.direction = (1, 0)
        self.next_direction = self.direction
        self.food = self.create_food()
        self.score = 0
        self.move_timer = 0
        self.paused = False
        self.game_over = False

    def create_food(self) -> tuple[int, int]:
        available = [
            (x, y)
            for y in range(GRID_ROWS)
            for x in range(GRID_COLUMNS)
            if (x, y) not in self.snake
        ]
        return random.choice(available)

    def set_direction(self, direction: tuple[int, int]) -> None:
        if direction[0] + self.direction[0] == 0 and direction[1] + self.direction[1] == 0:
            return
        self.next_direction = direction

    def move_snake(self) -> None:
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        direction_x, direction_y = self.direction
        new_head = (head_x + direction_x, head_y + direction_y)
        ate_food = new_head == self.food

        hits_wall = not (0 <= new_head[0] < GRID_COLUMNS and 0 <= new_head[1] < GRID_ROWS)
        body_to_check = self.snake if ate_food else self.snake[:-1]
        if hits_wall or new_head in body_to_check:
            self.end_game()
            return

        self.snake.insert(0, new_head)
        if ate_food:
            self.score += 10
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()
            self.food = self.create_food()
        else:
            self.snake.pop()

    def end_game(self) -> None:
        self.game_over = True
        self.paused = False

    def handle_key(self, event: pygame.event.Event) -> None:
        key = event.key
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.set_direction((-1, 0))
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.set_direction((1, 0))
        elif key in (pygame.K_UP, pygame.K_w):
            self.set_direction((0, -1))
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.set_direction((0, 1))
        elif key == pygame.K_p and not self.game_over:
            self.paused = not self.paused
        elif key in (pygame.K_SPACE, pygame.K_RETURN) and self.game_over:
            self.reset_game()

    def update(self, elapsed_ms: int) -> None:
        if self.paused or self.game_over:
            return
        self.move_timer += elapsed_ms
        while self.move_timer >= MOVE_INTERVAL:
            self.move_timer -= MOVE_INTERVAL
            self.move_snake()
            if self.game_over:
                break

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: tuple[int, int],
        center: bool = False,
    ) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(surface, rect)

    def draw_board(self) -> None:
        board_rect = pygame.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT)
        pygame.draw.rect(self.screen, BOARD_BACKGROUND, board_rect)
        for x in range(GRID_COLUMNS + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (x * CELL_SIZE, 0), (x * CELL_SIZE, BOARD_HEIGHT))
        for y in range(GRID_ROWS + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y * CELL_SIZE), (BOARD_WIDTH, y * CELL_SIZE))

        food_x, food_y = self.food
        food_rect = pygame.Rect(
            food_x * CELL_SIZE + 4,
            food_y * CELL_SIZE + 4,
            CELL_SIZE - 8,
            CELL_SIZE - 8,
        )
        pygame.draw.circle(self.screen, FOOD, food_rect.center, CELL_SIZE // 2 - 4)

        for index, (x, y) in enumerate(self.snake):
            rect = pygame.Rect(x * CELL_SIZE + 2, y * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            color = SNAKE_HEAD if index == 0 else SNAKE_BODY
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            if index == 0:
                self.draw_eyes(rect)

    def draw_eyes(self, rect: pygame.Rect) -> None:
        eye_color = (7, 25, 27)
        if self.direction[0] != 0:
            eye_x = rect.centerx + (4 if self.direction[0] > 0 else -4)
            points = [(eye_x, rect.centery - 4), (eye_x, rect.centery + 4)]
        else:
            eye_y = rect.centery + (4 if self.direction[1] > 0 else -4)
            points = [(rect.centerx - 4, eye_y), (rect.centerx + 4, eye_y)]
        for point in points:
            pygame.draw.circle(self.screen, eye_color, point, 2)

    def draw_panel(self) -> None:
        panel_rect = pygame.Rect(BOARD_WIDTH, 0, SIDE_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, PANEL_BACKGROUND, panel_rect)
        self.draw_text("NEON", self.title_font, TEXT, (BOARD_WIDTH + 24, 28))
        self.draw_text("SNAKE", self.title_font, ACCENT, (BOARD_WIDTH + 24, 62))
        pygame.draw.line(
            self.screen,
            (43, 61, 88),
            (BOARD_WIDTH + 24, 112),
            (WINDOW_WIDTH - 24, 112),
        )

        self.draw_text("점수", self.small_font, MUTED_TEXT, (BOARD_WIDTH + 24, 140))
        self.draw_text(str(self.score), self.heading_font, TEXT, (BOARD_WIDTH + 24, 161))
        self.draw_text("최고 점수", self.small_font, MUTED_TEXT, (BOARD_WIDTH + 24, 208))
        self.draw_text(str(self.high_score), self.heading_font, TEXT, (BOARD_WIDTH + 24, 229))

        self.draw_text("조작 방법", self.heading_font, TEXT, (BOARD_WIDTH + 24, 294))
        controls = ("방향키 / WASD  이동", "P  일시정지", "ESC  종료")
        for index, control in enumerate(controls):
            self.draw_text(control, self.small_font, MUTED_TEXT, (BOARD_WIDTH + 24, 330 + index * 24))

    def draw_overlay(self) -> None:
        if not self.paused and not self.game_over:
            return
        overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 20, 190))
        self.screen.blit(overlay, (0, 0))
        if self.game_over:
            title = "GAME OVER"
            subtitle = "스페이스 또는 Enter로 다시 시작"
            color = FOOD
        else:
            title = "일시정지"
            subtitle = "P를 눌러 계속하기"
            color = ACCENT
        self.draw_text(title, self.heading_font, color, (BOARD_WIDTH // 2, BOARD_HEIGHT // 2 - 20), center=True)
        self.draw_text(subtitle, self.small_font, TEXT, (BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 20), center=True)

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self.draw_board()
        self.draw_panel()
        self.draw_overlay()
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            elapsed_ms = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            self.update(elapsed_ms)
            self.draw()
        pygame.quit()


def main() -> None:
    SnakeGame().run()


if __name__ == "__main__":
    main()
