"""Flask backend for the Snake mini project (pointers a and b).

Routes
  GET  /                  -> health check
  GET  /api/config        -> game settings for the client
  POST /api/score         -> validate + save a score
  GET  /api/leaderboard   -> top scores (?limit=10)
  GET  /api/player/<name> -> one player's best score and games played

Run locally:  python app.py   (server starts on http://127.0.0.1:5000)
"""
import os
import sqlite3

from flask import Flask, g, jsonify, request

from game import (GRID, MAX_SCORE, MIN_TICK_MS, POINTS_PER_FOOD,
                  SPEEDUP_MS, START_TICK_MS)

app = Flask(__name__)
# Absolute path so it also works when deployed (e.g. PythonAnywhere).
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.db")
MAX_NAME_LEN = 20


# ---------- database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS scores (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   name       TEXT    NOT NULL,
                   score      INTEGER NOT NULL,
                   created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
               )"""
        )


init_db()


# ---------- routes ----------
@app.route("/", methods=["GET"])
def index():
    return jsonify(status="ok", message="Snake API is running")


@app.route("/api/config", methods=["GET"])
def config():
    return jsonify(
        grid=GRID,
        points_per_food=POINTS_PER_FOOD,
        start_tick_ms=START_TICK_MS,
        min_tick_ms=MIN_TICK_MS,
        speedup_ms=SPEEDUP_MS,
        max_score=MAX_SCORE,
    )


@app.route("/api/score", methods=["POST"])
def submit_score():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send a JSON body like {\"name\": \"Asha\", \"score\": 50}"), 400

    name = data.get("name")
    score = data.get("score")

    if not isinstance(name, str) or not name.strip():
        return jsonify(error="name must be a non-empty string"), 400
    name = name.strip()
    if len(name) > MAX_NAME_LEN:
        return jsonify(error=f"name must be at most {MAX_NAME_LEN} characters"), 400

    # bool is a subclass of int in Python, so reject it explicitly
    if not isinstance(score, int) or isinstance(score, bool):
        return jsonify(error="score must be an integer"), 400
    # Score checks using the shared game rules
    if score < 0 or score > MAX_SCORE:
        return jsonify(error=f"score must be between 0 and {MAX_SCORE}"), 400
    if score % POINTS_PER_FOOD != 0:
        return jsonify(error=f"score must be a multiple of {POINTS_PER_FOOD}"), 400

    db = get_db()
    cur = db.execute("INSERT INTO scores (name, score) VALUES (?, ?)", (name, score))
    db.commit()

    # rank = 1 + number of scores strictly higher than this one
    rank = db.execute(
        "SELECT COUNT(*) + 1 FROM scores WHERE score > ?", (score,)
    ).fetchone()[0]
    return jsonify(id=cur.lastrowid, name=name, score=score, rank=rank), 201


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify(error="limit must be an integer"), 400
    limit = max(1, min(limit, 100))

    rows = get_db().execute(
        "SELECT name, score, created_at FROM scores "
        "ORDER BY score DESC, created_at ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/player/<name>", methods=["GET"])
def player(name):
    row = get_db().execute(
        "SELECT MAX(score) AS best, COUNT(*) AS games FROM scores WHERE name = ?",
        (name,),
    ).fetchone()
    if row["games"] == 0:
        return jsonify(error="player not found"), 404
    return jsonify(name=name, best=row["best"], games=row["games"])


if __name__ == "__main__":
    app.run(debug=True)
