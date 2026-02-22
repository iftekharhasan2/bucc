import os
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "leaderboard.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT    NOT NULL,
                email     TEXT    NOT NULL,
                score     INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Return top 10 scores. One entry per email (best score only)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT name, email, MAX(score) AS score
            FROM scores
            GROUP BY email
            ORDER BY score DESC
            LIMIT 10
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/leaderboard", methods=["POST"])
def post_score():
    """Save a new score entry."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name  = str(data.get("name",  "")).strip()[:30]
    email = str(data.get("email", "")).strip()[:100]
    score = data.get("score", 0)

    if not name or not email or not isinstance(score, int) or score < 0:
        return jsonify({"error": "Missing or invalid fields"}), 400

    with get_db() as conn:
        conn.execute(
            "INSERT INTO scores (name, email, score) VALUES (?, ?, ?)",
            (name, email, score)
        )
        conn.commit()

        # Return this player's best rank
        rank_row = conn.execute("""
            SELECT rank FROM (
                SELECT email, RANK() OVER (ORDER BY MAX(score) DESC) AS rank
                FROM scores
                GROUP BY email
            ) WHERE email = ?
        """, (email,)).fetchone()

    return jsonify({"ok": True, "rank": rank_row["rank"] if rank_row else None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)