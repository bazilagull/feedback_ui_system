"""
Feedback UI — Flask Application
================================
Routes:
  GET  /                  → Feedback form
  POST /submit            → Handle feedback submission
  GET  /admin/login       → Admin login page
  POST /admin/login       → Authenticate admin
  GET  /admin/logout      → Logout admin
  GET  /admin/dashboard   → Reviews dashboard (protected)
  POST /admin/delete/<id> → Delete a review (protected)
  POST /admin/export      → Export reviews as CSV (protected)
"""

import sqlite3, csv, io, os
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

DATABASE = os.path.join(app.instance_path, "feedback.db")
os.makedirs(app.instance_path, exist_ok=True)

# ── Database helpers ───────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL,
            rating      TEXT    NOT NULL
                        CHECK(rating IN ('unhappy','neutral','satisfied','love')),
            comment     TEXT,
            submitted_at TEXT   NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS admins (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL
        );
    """)
    db.commit()

    # Create default admin if none exists
    row = db.execute("SELECT id FROM admins LIMIT 1").fetchone()
    if not row:
        hashed = generate_password_hash("admin123")
        db.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", hashed)
        )
        db.commit()
        print("  ✓ Default admin created  →  username: admin  |  password: admin123")

# ── Auth decorator ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to access the admin panel.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Helpers ────────────────────────────────────────────────────────────────────
RATING_META = {
    "unhappy":   {"emoji": "😞", "label": "Unhappy",   "color": "#f06060"},
    "neutral":   {"emoji": "😐", "label": "Neutral",   "color": "#60a5fa"},
    "satisfied": {"emoji": "😊", "label": "Satisfied", "color": "#3dd68c"},
    "love":      {"emoji": "🤩", "label": "Love it!",  "color": "#f5a623"},
}

# ── Public routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    submitted = session.pop("submitted", None)
    return render_template("index.html", submitted=submitted)

@app.route("/submit", methods=["POST"])
def submit():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    rating  = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    errors = []
    if not name or len(name) < 2:
        errors.append("Name must be at least 2 characters.")
    if not email or "@" not in email:
        errors.append("A valid email address is required.")
    if rating not in RATING_META:
        errors.append("Please select a valid rating.")
    if len(comment) > 300:
        errors.append("Comment must be 300 characters or fewer.")

    if errors:
        return render_template("index.html", errors=errors,
                               form_name=name, form_email=email,
                               form_rating=rating, form_comment=comment)

    db = get_db()
    db.execute(
        "INSERT INTO reviews (name, email, rating, comment) VALUES (?, ?, ?, ?)",
        (name, email, rating, comment or None)
    )
    db.commit()

    meta = RATING_META[rating]
    session["submitted"] = {"label": meta["label"], "emoji": meta["emoji"]}
    return redirect(url_for("index"))

# ── Admin routes ───────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = get_db().execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
            session.permanent = True
            session["admin_id"]   = admin["id"]
            session["admin_name"] = admin["username"]
            flash("Welcome back, {}!".format(admin["username"]), "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    db = get_db()

    # Filters
    search     = request.args.get("search", "").strip()
    filter_rating = request.args.get("rating", "all")
    sort_by    = request.args.get("sort", "newest")
    page       = max(1, int(request.args.get("page", 1)))
    per_page   = 10

    query  = "SELECT * FROM reviews WHERE 1=1"
    params = []

    if search:
        query  += " AND (name LIKE ? OR email LIKE ? OR comment LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]

    if filter_rating in RATING_META:
        query  += " AND rating = ?"
        params.append(filter_rating)

    order = "DESC" if sort_by == "newest" else "ASC"
    query += f" ORDER BY submitted_at {order}"

    # Total count for pagination
    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    query  += " LIMIT ? OFFSET ?"
    params += [per_page, (page - 1) * per_page]

    reviews = db.execute(query, params).fetchall()

    # Aggregate stats
    stats_rows = db.execute(
        "SELECT rating, COUNT(*) as cnt FROM reviews GROUP BY rating"
    ).fetchall()
    stats = {r["rating"]: r["cnt"] for r in stats_rows}
    total_reviews = sum(stats.values())

    total_pages = max(1, -(-total // per_page))  # ceiling division

    now = datetime.now().strftime("%B %d, %Y")
    return render_template(
        "admin/dashboard.html",
        now=now,
        reviews=reviews,
        stats=stats,
        rating_meta=RATING_META,
        total_reviews=total_reviews,
        total_pages=total_pages,
        current_page=page,
        search=search,
        filter_rating=filter_rating,
        sort_by=sort_by,
    )

@app.route("/admin/delete/<int:review_id>", methods=["POST"])
@login_required
def admin_delete(review_id):
    db = get_db()
    db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    db.commit()
    flash("Review deleted successfully.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))

@app.route("/admin/export")
@login_required
def admin_export():
    db  = get_db()
    rows = db.execute(
        "SELECT id, name, email, rating, comment, submitted_at FROM reviews ORDER BY submitted_at DESC"
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Rating", "Comment", "Submitted At"])
    for row in rows:
        writer.writerow([row["id"], row["name"], row["email"],
                         row["rating"], row["comment"] or "", row["submitted_at"]])

    filename = f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        init_db()
        print("  ✓ Database initialised")
    print("  ✓ Server running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
