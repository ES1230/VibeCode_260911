const canvas = document.getElementById("tetris");
const ctx = canvas.getContext("2d");
const nextCanvas = document.getElementById("next");
const nextCtx = nextCanvas.getContext("2d");

const scoreElement = document.getElementById("score");
const highScoreElement = document.getElementById("highScore");
const startButton = document.getElementById("startButton");
const pauseButton = document.getElementById("pauseButton");
const message = document.getElementById("message");

const COLS = 10;
const ROWS = 20;
const BLOCK = 30;

const pieces = [
    { matrix: [[1, 1, 1, 1]], color: "#22d3ee" },
    { matrix: [[1, 0, 0], [1, 1, 1]], color: "#6366f1" },
    { matrix: [[0, 0, 1], [1, 1, 1]], color: "#fb923c" },
    { matrix: [[1, 1], [1, 1]], color: "#facc15" },
    { matrix: [[0, 1, 1], [1, 1, 0]], color: "#4ade80" },
    { matrix: [[0, 1, 0], [1, 1, 1]], color: "#c084fc" },
    { matrix: [[1, 1, 0], [0, 1, 1]], color: "#f43f5e" }
];

let board;
let player;
let nextPiece;
let score = 0;
let highScore = Number(localStorage.getItem("neonTetrisHighScore")) || 0;
let running = false;
let paused = false;
let lastTime = 0;
let dropTimer = 0;
let animationId;

highScoreElement.textContent = highScore;

function createBoard() {
    return Array.from({ length: ROWS }, () => Array(COLS).fill(null));
}

function randomPiece() {
    const source = pieces[Math.floor(Math.random() * pieces.length)];

    return {
        matrix: source.matrix.map(row => [...row]),
        color: source.color,
        x: Math.floor(COLS / 2) - Math.ceil(source.matrix[0].length / 2),
        y: 0
    };
}

function drawBlock(context, x, y, color, size) {
    const gradient = context.createLinearGradient(
        x * size,
        y * size,
        (x + 1) * size,
        (y + 1) * size
    );

    gradient.addColorStop(0, "#ffffff");
    gradient.addColorStop(0.16, color);
    gradient.addColorStop(1, "#111827");

    context.fillStyle = gradient;
    context.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);

    context.strokeStyle = color;
    context.lineWidth = 1;
    context.strokeRect(x * size + 1, y * size + 1, size - 2, size - 2);
}

function drawGrid() {
    ctx.strokeStyle = "rgba(130, 150, 220, 0.12)";
    ctx.lineWidth = 1;

    for (let x = 0; x <= COLS; x++) {
        ctx.beginPath();
        ctx.moveTo(x * BLOCK, 0);
        ctx.lineTo(x * BLOCK, ROWS * BLOCK);
        ctx.stroke();
    }

    for (let y = 0; y <= ROWS; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * BLOCK);
        ctx.lineTo(COLS * BLOCK, y * BLOCK);
        ctx.stroke();
    }
}

function drawMatrix(context, matrix, offsetX, offsetY, color, size) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                drawBlock(context, x + offsetX, y + offsetY, color, size);
            }
        });
    });
}

function drawNext() {
    nextCtx.fillStyle = "#080b1b";
    nextCtx.fillRect(0, 0, 120, 120);

    const matrix = nextPiece.matrix;
    const offsetX = (4 - matrix[0].length / 2) / 2;
    const offsetY = (4 - matrix.length) / 2;

    drawMatrix(nextCtx, matrix, offsetX, offsetY, nextPiece.color, 24);
}

function draw() {
    ctx.fillStyle = "#080b1b";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGrid();

    board.forEach((row, y) => {
        row.forEach((color, x) => {
            if (color) drawBlock(ctx, x, y, color, BLOCK);
        });
    });

    if (player) {
        drawMatrix(ctx, player.matrix, player.x, player.y, player.color, BLOCK);
    }
}

function collides(piece = player) {
    for (let y = 0; y < piece.matrix.length; y++) {
        for (let x = 0; x < piece.matrix[y].length; x++) {
            if (!piece.matrix[y][x]) continue;

            const boardX = piece.x + x;
            const boardY = piece.y + y;

            if (
                boardX < 0 ||
                boardX >= COLS ||
                boardY >= ROWS ||
                (boardY >= 0 && board[boardY][boardX])
            ) {
                return true;
            }
        }
    }

    return false;
}

function merge() {
    player.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value && player.y + y >= 0) {
                board[player.y + y][player.x + x] = player.color;
            }
        });
    });
}

function clearLines() {
    let cleared = 0;

    for (let y = ROWS - 1; y >= 0; y--) {
        if (board[y].every(Boolean)) {
            board.splice(y, 1);
            board.unshift(Array(COLS).fill(null));
            cleared++;
            y++;
        }
    }

    if (cleared) {
        score += [0, 100, 300, 500, 800][cleared];
        scoreElement.textContent = score;

        if (score > highScore) {
            highScore = score;
            highScoreElement.textContent = highScore;
            localStorage.setItem("neonTetrisHighScore", highScore);
        }
    }
}

function rotateMatrix(matrix) {
    return matrix[0].map((_, index) =>
        matrix.map(row => row[index]).reverse()
    );
}

function rotate() {
    const oldMatrix = player.matrix;
    const oldX = player.x;

    player.matrix = rotateMatrix(player.matrix);

    if (collides()) {
        player.x++;
        if (collides()) player.x = oldX - 1;
        if (collides()) {
            player.matrix = oldMatrix;
            player.x = oldX;
        }
    }
}

function move(direction) {
    player.x += direction;

    if (collides()) {
        player.x -= direction;
    }
}

function drop() {
    player.y++;

    if (collides()) {
        player.y--;
        merge();
        clearLines();
        player = nextPiece;
        nextPiece = randomPiece();
        drawNext();

        if (collides()) {
            gameOver();
        }
    }

    dropTimer = 0;
}

function hardDrop() {
    while (!collides()) {
        player.y++;
    }

    player.y--;
    drop();
}

function gameOver() {
    running = false;
    pauseButton.disabled = true;
    message.querySelector("strong").textContent = "GAME OVER";
    startButton.textContent = "다시 시작";
    message.style.display = "flex";
    cancelAnimationFrame(animationId);
}

function update(time = 0) {
    if (!running) return;

    const delta = time - lastTime;
    lastTime = time;

    if (!paused) {
        dropTimer += delta;

        if (dropTimer > 700) {
            drop();
        }

        draw();
    }

    animationId = requestAnimationFrame(update);
}

function startGame() {
    board = createBoard();
    player = randomPiece();
    nextPiece = randomPiece();
    score = 0;
    paused = false;
    running = true;

    scoreElement.textContent = "0";
    pauseButton.disabled = false;
    pauseButton.textContent = "일시정지";
    message.style.display = "none";

    drawNext();
    cancelAnimationFrame(animationId);
    lastTime = performance.now();
    animationId = requestAnimationFrame(update);
}

function togglePause() {
    if (!running) return;

    paused = !paused;
    pauseButton.textContent = paused ? "계속하기" : "일시정지";
}

document.addEventListener("keydown", event => {
    if (!running || paused) {
        if (event.key.toLowerCase() === "p") togglePause();
        return;
    }

    if (["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp", " "].includes(event.key)) {
        event.preventDefault();
    }

    if (event.key === "ArrowLeft") move(-1);
    if (event.key === "ArrowRight") move(1);
    if (event.key === "ArrowDown") drop();
    if (event.key === "ArrowUp") rotate();
    if (event.key === " ") hardDrop();
    if (event.key.toLowerCase() === "p") togglePause();

    draw();
});

startButton.addEventListener("click", startGame);
pauseButton.addEventListener("click", togglePause);

board = createBoard();
player = randomPiece();
nextPiece = randomPiece();
draw();
drawNext();