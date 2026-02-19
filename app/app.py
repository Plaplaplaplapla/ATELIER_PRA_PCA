import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request

DB_PATH = os.getenv("DB_PATH", "/data/app.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backup")

app = Flask(__name__)

# ---------- DB helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
def get_last_backup_info():
    if not os.path.isdir(BACKUP_DIR):
        return None, None

    files = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if os.path.isfile(path):
            files.append((name, path))

    if not files:
        return None, None

    # Tes backups sont du type app-<epoch>.db
    pattern = re.compile(r"^app-(\d+)\.db$")

    with_epoch = []
    for name, path in files:
        m = pattern.match(name)
        if m:
            with_epoch.append((int(m.group(1)), name))

    now = datetime.now(timezone.utc).timestamp()

    if with_epoch:
        epoch, name = max(with_epoch, key=lambda t: t[0])
        age = int(max(0, now - epoch))
        return name, age

    # fallback : tri par date de modif si le naming change
    latest_name, latest_path = max(files, key=lambda t: os.path.getmtime(t[1]))
    age = int(max(0, now - os.path.getmtime(latest_path)))
    return latest_name, age
# ---------- Routes ----------

@app.get("/")
def hello():
    init_db()
    return jsonify(status="Bonjour tout le monde !")


@app.get("/health")
def health():
    init_db()
    return jsonify(status="ok")

@app.get("/add")
def add():
    init_db()

    msg = request.args.get("message", "hello")
    ts = datetime.utcnow().isoformat() + "Z"

    conn = get_conn()
    conn.execute(
        "INSERT INTO events (ts, message) VALUES (?, ?)",
        (ts, msg)
    )
    conn.commit()
    conn.close()

    return jsonify(
        status="added",
        timestamp=ts,
        message=msg
    )

@app.get("/consultation")
def consultation():
    init_db()

    conn = get_conn()
    cur = conn.execute(
        "SELECT id, ts, message FROM events ORDER BY id DESC LIMIT 50"
    )

    rows = [
        {"id": r[0], "timestamp": r[1], "message": r[2]}
        for r in cur.fetchall()
    ]

    conn.close()

    return jsonify(rows)

@app.get("/count")
def count():
    init_db()

    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM events")
    n = cur.fetchone()[0]
    conn.close()

    return jsonify(count=n)

# ---------- Main ----------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
