import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
DB_PATH = Path(os.environ.get("DATABASE_PATH", "cases.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD) if ADMIN_PASSWORD else None
STATUSES = ("Open", "In review", "Resolved", "Closed")
CATEGORIES = ("Harassment", "Impersonation", "Spam", "Scam", "Other")


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            platform TEXT NOT NULL,
            reference TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL
        )""")


init_db()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post():
    if request.method == "POST":
        supplied = request.form.get("csrf_token", "")
        expected = session.get("csrf", "")
        if not expected or not secrets.compare_digest(supplied, expected):
            abort(400, "Invalid form token. Reload the page and try again.")


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


BASE = """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{{ title }} · CaseDesk</title><style>
:root{color-scheme:light dark;--bg:#f4f6fb;--panel:#fff;--ink:#182033;--muted:#667085;--line:#e2e7f0;--accent:#315ce8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}header{background:var(--panel);border-bottom:1px solid var(--line);padding:14px max(18px,calc((100% - 1000px)/2));display:flex;justify-content:space-between;gap:12px;align-items:center}header a{color:var(--accent);text-decoration:none;font-weight:650}.wrap{max-width:1000px;margin:28px auto;padding:0 18px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px}h1{font-size:1.55rem;margin:0 0 16px}h2{font-size:1.15rem;margin:0 0 12px}label{display:block;font-weight:600;margin:12px 0 5px}input,select,textarea{width:100%;padding:11px;border:1px solid #bfc8d8;border-radius:8px;background:var(--panel);color:var(--ink);font:inherit}textarea{min-height:110px;resize:vertical}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.btn{display:inline-block;border:0;border-radius:8px;padding:10px 15px;background:var(--accent);color:white;font:inherit;font-weight:650;text-decoration:none;cursor:pointer;margin-top:14px}.btn.secondary{background:#e9edf7;color:#25314b}.flash{padding:10px 12px;background:#fff3cd;border-radius:8px;margin-bottom:12px}.case{border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0}.case-top{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.muted{color:var(--muted);font-size:.9rem}.pill{display:inline-block;background:#edf1ff;color:#2949b8;border-radius:20px;padding:3px 9px;font-size:.82rem}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.actions form{display:flex;gap:8px;align-items:center}.actions select{width:auto;max-width:150px;padding:7px}.actions .btn{margin:0;padding:8px 12px}@media(max-width:600px){.grid{grid-template-columns:1fr}.wrap{margin:16px auto}.panel{padding:16px}header{padding:12px 18px}}
@media(prefers-color-scheme:dark){:root{--bg:#101522;--panel:#171e2d;--ink:#edf1fa;--muted:#a5afc2;--line:#30394c}input,select,textarea{border-color:#475269}.btn.secondary{background:#30394c;color:#edf1fa}.pill{background:#27345e;color:#c9d5ff}}
</style></head><body><header><a href='{{ url_for("index") }}'>CaseDesk</a>{% if session.get('authenticated') %}<a href='{{ url_for("logout") }}'>Sign out</a>{% endif %}</header><main class='wrap'>{% with messages=get_flashed_messages() %}{% for message in messages %}<div class='flash'>{{ message }}</div>{% endfor %}{% endwith %}{{ body|safe }}</main></body></html>"""

LOGIN = """<section class='panel'><h1>Sign in</h1>{% if not password_configured %}<p>Set the <code>ADMIN_PASSWORD</code> environment variable before using this app.</p>{% else %}<form method='post'><input type='hidden' name='csrf_token' value='{{ csrf_token() }}'><label for='password'>Admin password</label><input id='password' name='password' type='password' required autocomplete='current-password'><button class='btn' type='submit'>Sign in</button></form>{% endif %}</section>"""

DASH = """<section class='panel'><h1>Complaint case manager</h1><p class='muted'>Track reports you choose to submit through the relevant platform's official process. This tool does not send reports or automate enforcement.</p><form method='post' action='{{ url_for("create_case") }}'><input type='hidden' name='csrf_token' value='{{ csrf_token() }}'><div class='grid'><div><label for='subject'>Case title</label><input id='subject' name='subject' maxlength='120' required></div><div><label for='category'>Category</label><select id='category' name='category'>{% for c in categories %}<option>{{ c }}</option>{% endfor %}</select></div><div><label for='platform'>Platform / service</label><input id='platform' name='platform' maxlength='80' required></div><div><label for='reference'>Public URL or case reference (optional)</label><input id='reference' name='reference' maxlength='500' type='url' placeholder='https://…'></div></div><label for='notes'>Evidence notes (avoid passwords or private personal data)</label><textarea id='notes' name='notes' maxlength='5000' required></textarea><button class='btn' type='submit'>Add case</button></form></section><section class='panel'><h2>Cases ({{ cases|length }})</h2><form method='get' class='grid'><div><label for='q'>Search</label><input id='q' name='q' value='{{ q }}' placeholder='Title, platform, notes'></div><div><label for='status'>Status</label><select id='status' name='status'><option value=''>All statuses</option>{% for s in statuses %}<option {% if status==s %}selected{% endif %}>{{ s }}</option>{% endfor %}</select></div></div><button class='btn secondary' type='submit'>Filter</button></form>{% for c in cases %}<article class='case'><div class='case-top'><strong>#{{ c.id }} · {{ c.subject }}</strong><span class='pill'>{{ c.status }}</span></div><p class='muted'>{{ c.category }} · {{ c.platform }} · {{ c.created_at }}</p><p>{{ c.notes }}</p>{% if c.reference %}<p><a href='{{ c.reference }}' target='_blank' rel='noopener noreferrer'>Open reference</a></p>{% endif %}<div class='actions'><form method='post' action='{{ url_for("update_case", case_id=c.id) }}'><input type='hidden' name='csrf_token' value='{{ csrf_token() }}'><select name='status' aria-label='New status'>{% for s in statuses %}<option {% if c.status==s %}selected{% endif %}>{{ s }}</option>{% endfor %}</select><button class='btn' type='submit'>Update</button></form><a class='btn secondary' href='{{ url_for("export_case", case_id=c.id) }}'>Export draft</a><form method='post' action='{{ url_for("delete_case", case_id=c.id) }}' onsubmit='return confirm("Delete this case?")'><input type='hidden' name='csrf_token' value='{{ csrf_token() }}'><button class='btn secondary' type='submit'>Delete</button></form></div></article>{% else %}<p class='muted'>No cases match. Add one above.</p>{% endfor %}</section>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if PASSWORD_HASH and check_password_hash(PASSWORD_HASH, request.form.get("password", "")):
            session.clear()
            session["authenticated"] = True
            session["csrf"] = secrets.token_urlsafe(24)
            return redirect(url_for("index"))
        flash("Incorrect password.")
    return render_template_string(BASE, title="Sign in", body=render_template_string(LOGIN, password_configured=bool(PASSWORD_HASH)))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    q = request.args.get("q", "")[:120].strip()
    status = request.args.get("status", "")
    if status not in STATUSES:
        status = ""
    sql = "SELECT * FROM cases"
    args = []
    clauses = []
    if q:
        clauses.append("(subject LIKE ? OR platform LIKE ? OR notes LIKE ?)")
        args.extend([f"%{q}%"] * 3)
    if status:
        clauses.append("status = ?")
        args.append(status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT 200"
    with connect_db() as db:
        cases = db.execute(sql, args).fetchall()
    body = render_template_string(DASH, cases=cases, q=q, status=status, statuses=STATUSES, categories=CATEGORIES)
    return render_template_string(BASE, title="Cases", body=body)


@app.post("/cases")
@login_required
def create_case():
    subject = request.form.get("subject", "").strip()[:120]
    category = request.form.get("category", "Other")
    platform = request.form.get("platform", "").strip()[:80]
    reference = request.form.get("reference", "").strip()[:500]
    notes = request.form.get("notes", "").strip()[:5000]
    if not subject or not platform or not notes or category not in CATEGORIES:
        flash("Please complete the required fields.")
        return redirect(url_for("index"))
    if reference and not (reference.startswith("https://") or reference.startswith("http://")):
        flash("Reference must be an http(s) URL.")
        return redirect(url_for("index"))
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with connect_db() as db:
        db.execute("INSERT INTO cases(subject,category,platform,reference,notes,created_at) VALUES(?,?,?,?,?,?)", (subject, category, platform, reference, notes, created))
    flash("Case added.")
    return redirect(url_for("index"))


@app.post("/cases/<int:case_id>/status")
@login_required
def update_case(case_id):
    status = request.form.get("status", "")
    if status not in STATUSES:
        abort(400)
    with connect_db() as db:
        result = db.execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))
    if result.rowcount == 0:
        abort(404)
    flash("Status updated.")
    return redirect(url_for("index"))


@app.post("/cases/<int:case_id>/delete")
@login_required
def delete_case(case_id):
    with connect_db() as db:
        result = db.execute("DELETE FROM cases WHERE id=?", (case_id,))
    if result.rowcount == 0:
        abort(404)
    flash("Case deleted.")
    return redirect(url_for("index"))


@app.get("/cases/<int:case_id>/export")
@login_required
def export_case(case_id):
    with connect_db() as db:
        case = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        abort(404)
    text = (f"Complaint draft — Case #{case['id']}\n\nSubject: {case['subject']}\nCategory: {case['category']}\nPlatform: {case['platform']}\nReference: {case['reference']}\n\nEvidence notes:\n{case['notes']}\n\nPlease review this information and submit through the platform's official reporting process if appropriate.\n")
    from flask import Response
    return Response(text, mimetype="text/plain", headers={"Content-Disposition": f"attachment; filename=case-{case_id}-draft.txt"})


@app.errorhandler(400)
def bad_request(error):
    return render_template_string(BASE, title="Bad request", body="<section class='panel'><h1>Bad request</h1><p>Reload and try again.</p></section>"), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
