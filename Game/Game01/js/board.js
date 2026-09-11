// This file manages the game board state, including the grid, collision detection, and line clearing logic.

class Board {
    constructor() {
        this.grid = this.createGrid();
        this.score = 0;
    }

    createGrid() {
        const rows = 20;
        const cols = 10;
        return Array.from({ length: rows }, () => Array(cols).fill(0));
    }

    drawBoard(context) {
        for (let row = 0; row < this.grid.length; row++) {
            for (let col = 0; col < this.grid[row].length; col++) {
                context.fillStyle = this.grid[row][col] ? 'blue' : 'white';
                context.fillRect(col * 30, row * 30, 30, 30);
                context.strokeRect(col * 30, row * 30, 30, 30);
            }
        }
    }

    addPiece(piece, position) {
        piece.shape.forEach((row, r) => {
            row.forEach((value, c) => {
                if (value) {
                    this.grid[position.y + r][position.x + c] = value;
                }
            });
        });
    }

    checkCollision(piece, position) {
        for (let r = 0; r < piece.shape.length; r++) {
            for (let c = 0; c < piece.shape[r].length; c++) {
                if (piece.shape[r][c] && 
                    (this.grid[position.y + r] === undefined || 
                     this.grid[position.y + r][position.x + c] === undefined || 
                     this.grid[position.y + r][position.x + c])) {
                    return true;
                }
            }
        }
        return false;
    }

    clearLines() {
        for (let r = this.grid.length - 1; r >= 0; r--) {
            if (this.grid[r].every(value => value !== 0)) {
                this.grid.splice(r, 1);
                this.grid.unshift(Array(this.grid[0].length).fill(0));
                this.score += 100;
                r++; // Check the same row again
            }
        }
    }
}