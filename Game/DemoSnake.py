"""Standalone Tkinter port of the Game01 Neon Tetris game."""

from __future__ import annotations

import json
import random
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


COLS = 10
ROWS = 20
BLOCK = 30
BOARD_WIDTH = COLS * BLOCK
BOARD_HEIGHT = ROWS * BLOCK
DROP_INTERVAL = 700
HIGH_SCORE_FILE = Path(__file__).with_name("neon_tetris_high_score.json")

PIECES = (
    ("I", ((1, 1, 1, 1),), "#22d3ee"),
    ("J", ((0, 0, 1), (1, 1, 1)), "#6366f1"),
    ("L", ((1, 0, 0), (1, 1, 1)), "#fb923c"),
    ("O", ((1, 1), (1, 1)), "#facc15"),
    ("S", ((0, 1, 1), (1, 1, 0)), "#4ade80"),
    ("T", ((0, 1, 0), (1, 1, 1)), "#c084fc"),
    ("Z", ((1, 1, 0), (0, 1, 1)), "#f43f5e"),
)


@dataclass
class Piece:
    matrix: list[list[int]]
    color: str
    x: int
    y: int


class NeonTetris:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Neon Tetris")
        self.root.configure(bg="#11152a")
        self.root.resizable(False, False)

        self.board: list[list[Optional[str]]] = self.create_board()
        self.player: Optional[Piece] = None
        self.next_piece: Optional[Piece] = None
        self.score = 0
        self.high_score = self.load_high_score()
        self.running = False
        self.paused = False
        self.drop_timer = 0
        self.after_id: Optional[str] = None

        self.build_ui()
        self.root.bind("<KeyPress>", self.handle_key)
        self.draw()

    @staticmethod
    def create_board() -> list[list[Optional[str]]]:
        return [[None for _ in range(COLS)] for _ in range(ROWS)]

    @staticmethod
    def load_high_score() -> int:
        try:
            value = json.loads(HIGH_SCORE_FILE.read_text(encoding="utf-8"))
            return int(value) if isinstance(value, int) else 0
        except (OSError, ValueError, TypeError):
            return 0

    def save_high_score(self) -> None:
        try:
            HIGH_SCORE_FILE.write_text(
                json.dumps(self.high_score), encoding="utf-8"
            )
        except OSError:
            pass

    def build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#11152a", padx=24, pady=20)
        outer.pack()

        title = tk.Label(
            outer,
            text="NEON TETRIS",
            fg="#f8fafc",
            bg="#11152a",
            font=("Segoe UI", 24, "bold"),
        )
        title.pack()
        tk.Label(
            outer,
            text="블록을 쌓고 최고 점수에 도전하세요",
            fg="#94a3b8",
            bg="#11152a",
            font=("Segoe UI", 10),
        ).pack(pady=(2, 16))

        layout = tk.Frame(outer, bg="#11152a")
        layout.pack()

        board_frame = tk.Frame(layout, bg="#080b1b", padx=6, pady=6)
        board_frame.grid(row=0, column=0, padx=(0, 18))
        self.canvas = tk.Canvas(
            board_frame,
            width=BOARD_WIDTH,
            height=BOARD_HEIGHT,
            bg="#080b1b",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.message_frame = tk.Frame(
            self.canvas, bg="#11152a", highlightbackground="#334155", highlightthickness=1
        )
        self.message_title = tk.Label(
            self.message_frame,
            text="NEON TETRIS",
            fg="#f8fafc",
            bg="#11152a",
            font=("Segoe UI", 16, "bold"),
        )
        self.message_title.pack(padx=22, pady=(16, 10))
        self.start_button = tk.Button(
            self.message_frame,
            text="게임 시작",
            command=self.start_game,
            fg="#08111f",
            bg="#22d3ee",
            activebackground="#67e8f9",
            relief="flat",
            padx=14,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        self.start_button.pack(padx=22, pady=(0, 16))
        self.message_window = self.canvas.create_window(
            BOARD_WIDTH // 2, BOARD_HEIGHT // 2, window=self.message_frame
        )

        panel = tk.Frame(layout, bg="#11152a", width=150)
        panel.grid(row=0, column=1, sticky="n")
        panel.grid_propagate(False)

        self.score_label = self.make_info_box(panel, "점수", "0")
        self.high_score_label = self.make_info_box(panel, "최고 점수", str(self.high_score))

        next_box = tk.Frame(panel, bg="#1d2540", padx=10, pady=8)
        next_box.pack(fill="x", pady=(0, 12))
        tk.Label(
            next_box, text="다음 블록", fg="#cbd5e1", bg="#1d2540", font=("Segoe UI", 10)
        ).pack(anchor="w")
        self.next_canvas = tk.Canvas(
            next_box, width=120, height=120, bg="#080b1b", highlightthickness=0
        )
        self.next_canvas.pack(pady=(6, 0))

        self.pause_button = tk.Button(
            panel,
            text="일시정지",
            command=self.toggle_pause,
            state=tk.DISABLED,
            fg="#e2e8f0",
            bg="#26324f",
            activebackground="#334155",
            relief="flat",
            pady=7,
            font=("Segoe UI", 10, "bold"),
        )
        self.pause_button.pack(fill="x", pady=(0, 14))

        controls = tk.Frame(panel, bg="#11152a")
        controls.pack(fill="x")
        tk.Label(
            controls, text="조작 방법", fg="#f8fafc", bg="#11152a", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        for text in ("← → 이동", "↑ 회전", "↓ 빠르게 내리기", "스페이스 즉시 내리기", "P 일시정지"):
            tk.Label(
                controls, text=text, fg="#94a3b8", bg="#11152a", anchor="w", font=("Segoe UI", 9)
            ).pack(fill="x", pady=1)

    @staticmethod
    def make_info_box(parent: tk.Widget, caption: str, value: str) -> tk.Label:
        box = tk.Frame(parent, bg="#1d2540", padx=12, pady=8)
        box.pack(fill="x", pady=(0, 10))
        tk.Label(box, text=caption, fg="#cbd5e1", bg="#1d2540", font=("Segoe UI", 9)).pack(anchor="w")
        label = tk.Label(box, text=value, fg="#f8fafc", bg="#1d2540", font=("Segoe UI", 20, "bold"))
        label.pack(anchor="w")
        return label

    def random_piece(self) -> Piece:
        _, source, color = random.choice(PIECES)
        matrix = [list(row) for row in source]
        return Piece(matrix, color, COLS // 2 - len(matrix[0]) // 2, 0)

    def start_game(self) -> None:
        self.board = self.create_board()
        self.player = self.random_piece()
        self.next_piece = self.random_piece()
        self.score = 0
        self.drop_timer = 0
        self.paused = False
        self.running = True
        self.score_label.configure(text="0")
        self.pause_button.configure(state=tk.NORMAL, text="일시정지")
        self.canvas.itemconfigure(self.message_window, state="hidden")
        self.draw_next()
        self.schedule_update()

    def schedule_update(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(50, self.update)

    def update(self) -> None:
        self.after_id = None
        if not self.running:
            return
        if not self.paused:
            self.drop_timer += 50
            if self.drop_timer > DROP_INTERVAL:
                self.drop()
            self.draw()
        self.schedule_update()

    def collides(self, piece: Optional[Piece] = None) -> bool:
        target = piece or self.player
        if target is None:
            return False
        for y, row in enumerate(target.matrix):
            for x, value in enumerate(row):
                if not value:
                    continue
                board_x = target.x + x
                board_y = target.y + y
                if board_x < 0 or board_x >= COLS or board_y >= ROWS:
                    return True
                if board_y >= 0 and self.board[board_y][board_x]:
                    return True
        return False

    def merge(self) -> None:
        if self.player is None:
            return
        for y, row in enumerate(self.player.matrix):
            for x, value in enumerate(row):
                board_y = self.player.y + y
                board_x = self.player.x + x
                if value and board_y >= 0:
                    self.board[board_y][board_x] = self.player.color

    def clear_lines(self) -> None:
        cleared = 0
        row = ROWS - 1
        while row >= 0:
            if all(self.board[row]):
                self.board.pop(row)
                self.board.insert(0, [None] * COLS)
                cleared += 1
            else:
                row -= 1
        if cleared:
            self.score += (0, 100, 300, 500, 800)[cleared]
            self.score_label.configure(text=str(self.score))
            if self.score > self.high_score:
                self.high_score = self.score
                self.high_score_label.configure(text=str(self.high_score))
                self.save_high_score()

    @staticmethod
    def rotate_matrix(matrix: list[list[int]]) -> list[list[int]]:
        return [list(row) for row in zip(*matrix[::-1])]

    def rotate(self) -> None:
        if self.player is None:
            return
        old_matrix = self.player.matrix
        old_x = self.player.x
        self.player.matrix = self.rotate_matrix(self.player.matrix)
        if self.collides():
            self.player.x += 1
            if self.collides():
                self.player.x = old_x - 1
            if self.collides():
                self.player.matrix = old_matrix
                self.player.x = old_x

    def move(self, direction: int) -> None:
        if self.player is None:
            return
        self.player.x += direction
        if self.collides():
            self.player.x -= direction

    def drop(self) -> None:
        if self.player is None:
            return
        self.player.y += 1
        if self.collides():
            self.player.y -= 1
            self.merge()
            self.clear_lines()
            self.player = self.next_piece
            self.next_piece = self.random_piece()
            self.draw_next()
            if self.collides():
                self.game_over()
        self.drop_timer = 0

    def hard_drop(self) -> None:
        if self.player is None:
            return
        while not self.collides():
            self.player.y += 1
        self.player.y -= 1
        self.drop()

    def game_over(self) -> None:
        self.running = False
        self.pause_button.configure(state=tk.DISABLED)
        self.message_title.configure(text="GAME OVER")
        self.start_button.configure(text="다시 시작")
        self.canvas.itemconfigure(self.message_window, state="normal")

    def toggle_pause(self) -> None:
        if not self.running:
            return
        self.paused = not self.paused
        self.pause_button.configure(text="계속하기" if self.paused else "일시정지")

    def handle_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "p":
            self.toggle_pause()
            return
        if not self.running or self.paused:
            return
        if key == "left":
            self.move(-1)
        elif key == "right":
            self.move(1)
        elif key == "down":
            self.drop()
        elif key == "up":
            self.rotate()
        elif key == "space":
            self.hard_drop()
        self.draw()

    def draw_block(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        color: str,
        size: int,
        tag: Optional[str] = None,
    ) -> None:
        left = x * size + 1
        top = y * size + 1
        right = (x + 1) * size - 1
        bottom = (y + 1) * size - 1
        canvas.create_rectangle(left, top, right, bottom, fill=color, outline=color, tags=tag)
        canvas.create_rectangle(
            left + 3,
            top + 3,
            right - 3,
            top + 7,
            fill="#ffffff",
            outline="",
            tags=tag,
        )

    def draw_matrix(
        self,
        canvas: tk.Canvas,
        matrix: list[list[int]],
        offset_x: float,
        offset_y: float,
        color: str,
        size: int,
        tag: Optional[str] = None,
    ) -> None:
        for y, row in enumerate(matrix):
            for x, value in enumerate(row):
                if value:
                    self.draw_block(canvas, x + offset_x, y + offset_y, color, size, tag)

    def draw_next(self) -> None:
        self.next_canvas.delete("all")
        if self.next_piece is None:
            return
        matrix = self.next_piece.matrix
        offset_x = (4 - len(matrix[0]) / 2) / 2
        offset_y = (4 - len(matrix)) / 2
        self.draw_matrix(self.next_canvas, matrix, offset_x, offset_y, self.next_piece.color, 24)

    def draw(self) -> None:
        self.canvas.delete("game")
        for x in range(COLS + 1):
            self.canvas.create_line(
                x * BLOCK, 0, x * BLOCK, BOARD_HEIGHT, fill="#1d2945", tags="game"
            )
        for y in range(ROWS + 1):
            self.canvas.create_line(
                0, y * BLOCK, BOARD_WIDTH, y * BLOCK, fill="#1d2945", tags="game"
            )
        for y, row in enumerate(self.board):
            for x, color in enumerate(row):
                if color:
                    self.draw_block(self.canvas, x, y, color, BLOCK, "game")
        if self.player:
            self.draw_matrix(
                self.canvas,
                self.player.matrix,
                self.player.x,
                self.player.y,
                self.player.color,
                BLOCK,
                "game",
            )
        if not self.running:
            self.canvas.itemconfigure(self.message_window, state="normal")


def main() -> None:
    root = tk.Tk()
    NeonTetris(root)
    root.mainloop()


if __name__ == "__main__":
    main()
