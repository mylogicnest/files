"""Pure game rules, shared by the client (play) and the server (score checks)."""
import random

GRID = 20
POINTS_PER_FOOD = 10
START_TICK_MS = 130
MIN_TICK_MS = 60
SPEEDUP_MS = 4
MAX_SCORE = GRID * GRID * POINTS_PER_FOOD

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


class SnakeGame:
    def __init__(self, grid=GRID, rng=None):
        self.grid = grid
        self.rng = rng or random.Random()
        mid = grid // 2
        self.snake = [(mid, mid), (mid - 1, mid), (mid - 2, mid)]  # head first
        self.direction = RIGHT
        self._queue = []          # buffered turns so fast key presses aren't lost
        self.score = 0
        self.tick_ms = START_TICK_MS
        self.alive = True
        self.won = False
        self.food = None
        self._place_food()

    def _place_food(self):
        taken = set(self.snake)
        free = [(x, y) for x in range(self.grid) for y in range(self.grid) if (x, y) not in taken]
        self.food = self.rng.choice(free) if free else None

    def turn(self, new_dir):
        """Queue a turn. Reversing straight into yourself is ignored."""
        ref = self._queue[-1] if self._queue else self.direction
        if new_dir == ref or (new_dir[0] == -ref[0] and new_dir[1] == -ref[1]):
            return
        if len(self._queue) < 2:
            self._queue.append(new_dir)

    def step(self):
        """Advance one tick. Returns True if the game is still running."""
        if not self.alive:
            return False
        if self._queue:
            self.direction = self._queue.pop(0)

        hx, hy = self.snake[0]
        head = (hx + self.direction[0], hy + self.direction[1])
        eating = head == self.food
        body = self.snake if eating else self.snake[:-1]  # tail moves away unless growing

        out = not (0 <= head[0] < self.grid and 0 <= head[1] < self.grid)
        if out or head in body:
            self.alive = False
            return False

        self.snake.insert(0, head)
        if eating:
            self.score += POINTS_PER_FOOD
            self.tick_ms = max(MIN_TICK_MS, self.tick_ms - SPEEDUP_MS)
            self._place_food()
            if self.food is None:
                self.alive, self.won = False, True
                return False
        else:
            self.snake.pop()
        return True
