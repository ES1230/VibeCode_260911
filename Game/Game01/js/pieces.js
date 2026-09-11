// pieces.js

const TETROMINOS = {
    I: [
        [1, 1, 1, 1]
    ],
    J: [
        [0, 0, 1],
        [1, 1, 1]
    ],
    L: [
        [1, 0, 0],
        [1, 1, 1]
    ],
    O: [
        [1, 1],
        [1, 1]
    ],
    S: [
        [0, 1, 1],
        [1, 1, 0]
    ],
    T: [
        [0, 1, 0],
        [1, 1, 1]
    ],
    Z: [
        [1, 1, 0],
        [0, 1, 1]
    ]
};

function rotate(piece) {
    return piece[0].map((_, index) => piece.map(row => row[index]).reverse());
}

function getRandomPiece() {
    const pieces = Object.keys(TETROMINOS);
    const randomPiece = pieces[Math.floor(Math.random() * pieces.length)];
    return TETROMINOS[randomPiece];
}