from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import psycopg2, os, random, string

app = Flask(__name__)
CORS(app)

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        database=os.environ.get("DB_NAME", "linksnap"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "postgres")
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id SERIAL PRIMARY KEY,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    code = generate_code()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO links (short_code, original_url) VALUES (%s, %s)", (code, url))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"short_code": code, "short_url": f"/r/{code}"})

@app.route("/api/links")
def list_links():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT short_code, original_url, clicks, created_at FROM links ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"short_code": r[0], "original_url": r[1], "clicks": r[2], "created_at": str(r[3])}
        for r in rows
    ])

@app.route("/r/<code>")
def redirect_url(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE links SET clicks = clicks + 1 WHERE short_code = %s RETURNING original_url", (code,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if row:
        return redirect(row[0])
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
