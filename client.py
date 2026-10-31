"""Turtle frontend for the Snake mini project (pointer c).

It plays the game locally using game.py, and talks to the Flask backend
through the API using the `requests` library:
  - GET  /api/config       at start-up
  - POST /api/score        when the game ends
  - GET  /api/leaderboard  to show the top scores

Start the server first (python3 app.py), then run:  python3 client.py
"""
import turtle

import requests

from game import (DOWN, GRID, LEFT, RIGHT, UP, SnakeGame)

SERVER = "http://127.0.0.1:5000"   # change to your deployed URL after deployment
TIMEOUT = 3                        # seconds, so the game never hangs on a bad network
CELL = 20


# ---------- API calls ----------
def get_config():
    try:
        r = requests.get(f"{SERVER}/api/config", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def post_score(name, score):
    try:
        r = requests.post(f"{SERVER}/api/score",
                          json={"name": name, "score": score}, timeout=TIMEOUT)
        if r.status_code == 201:
            return r.json()
        return {"error": r.json().get("error", "server rejected the score")}
    except requests.RequestException:
        return {"error": "could not reach the server"}


def get_leaderboard(limit=5):
    try:
        r = requests.get(f"{SERVER}/api/leaderboard",
                         params={"limit": limit}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


# ---------- setup ----------
config = get_config()
grid = config["grid"] if config else GRID
online = config is not None

top = get_leaderboard(1) if online else None
high_score = top[0]["score"] if top else 0

# Ask for the name in the TERMINAL (a turtle popup steals keyboard focus on macOS)
player_name = (input("Enter your name (max 20 characters): ") or "Player").strip()[:20] or "Player"

size = grid * CELL
screen = turtle.Screen()
screen.title("Snake" if online else "Snake (server offline - scores will not be saved)")
screen.bgcolor("black")
screen.setup(size + 40, size + 120)
screen.tracer(0)

# one turtle stamps the snake and food, one writes text
brush = turtle.Turtle()
brush.hideturtle()
brush.penup()
brush.shape("square")
brush.shapesize(CELL / 20 * 0.9)

# the apple is its own turtle: it is moved, never re-stamped, so it can't vanish
apple = turtle.Turtle()
apple.penup()
apple.shape("circle")
apple.shapesize(CELL / 20 * 0.9)
apple.color("red")

hud = turtle.Turtle()
hud.hideturtle()
hud.penup()
hud.color("white")

text = turtle.Turtle()
text.hideturtle()
text.penup()
text.color("white")

border = turtle.Turtle()
border.hideturtle()
border.color("gray")
border.penup()
border.goto(-size / 2, -size / 2 - 20)
border.pendown()
for _ in range(2):
    border.forward(size)
    border.left(90)
    border.forward(size)
    border.left(90)

state = {"game": None, "name": player_name, "running": False, "high": high_score}


def to_screen(cell):
    x, y = cell
    return (-size / 2 + x * CELL + CELL / 2,
            size / 2 - y * CELL - CELL / 2 - 20)


def draw():
    game = state["game"]
    brush.clearstamps()
    if game.food:
        apple.goto(to_screen(game.food))
        apple.showturtle()
    else:
        apple.hideturtle()
    for i, cell in enumerate(game.snake):
        brush.color("yellow" if i == 0 else "green")
        brush.goto(to_screen(cell))
        brush.stamp()
    hud.clear()
    high = max(state["high"], game.score)          # high score updates live
    status = "online" if online else "OFFLINE"
    hud.goto(0, size / 2 - 10)                     # just above the board
    hud.write(f"Score: {game.score}   |   High: {high}",
              align="center", font=("Courier", 16, "bold"))
    # same info in the window title bar, so it is always visible
    screen.title(f"Snake - {state['name']} ({status}) - Score: {game.score}  High: {high}")
    screen.update()


def tick():
    game = state["game"]
    if not state["running"]:
        return
    if game.step():
        draw()
        screen.ontimer(tick, game.tick_ms)
    else:
        draw()
        end_game()


def end_game():
    state["running"] = False
    game = state["game"]
    new_high = game.score > state["high"]
    state["high"] = max(state["high"], game.score)
    draw()                                          # refresh header with final high score
    result = post_score(state["name"], game.score) if online else None

    lines = ["YOU WIN!" if game.won else "GAME OVER", f"Score: {game.score}"]
    if result and "rank" in result:
        lines.append(f"Your rank: #{result['rank']}")
    elif result:
        lines.append(f"(not saved: {result['error']})")
    if new_high:
        lines.append("NEW HIGH SCORE!")

    board = get_leaderboard() if online else None
    if board:
        lines.append("")
        lines.append("--- Top scores ---")
        for i, row in enumerate(board, 1):
            lines.append(f"{i}. {row['name']}  {row['score']}")
    lines += ["", "Press SPACE to play again, Q to quit"]

    text.clear()
    text.goto(0, -len(lines) * 8)
    text.write("\n".join(lines), align="center", font=("Courier", 14, "bold"))
    screen.update()


def new_game():
    text.clear()
    state["game"] = SnakeGame(grid=grid)
    state["running"] = True
    draw()
    screen.ontimer(tick, state["game"].tick_ms)


def restart():
    if not state["running"]:
        new_game()


def quit_game():
    turtle.bye()


def bind_turn(keys, direction):
    for key in keys:
        screen.onkeypress(lambda d=direction: state["game"].turn(d), key)


bind_turn(["Up", "w"], UP)
bind_turn(["Down", "s"], DOWN)
bind_turn(["Left", "a"], LEFT)
bind_turn(["Right", "d"], RIGHT)
screen.onkeypress(restart, "space")
screen.onkeypress(quit_game, "q")

new_game()
screen.getcanvas().focus_force()   # make the game window take keyboard focus
screen.listen()                    # start listening for keys
screen.mainloop()