#!/usr/bin/env python3
"""
NXB Bank Micro Loan Portal (TRAINING SIMULATION - INTENTIONALLY VULNERABLE)
============================================================================
This is a synthetic training application built for an authorized, isolated
penetration-testing course lab (IE3132 CTF Play Box). It contains ONE
deliberately introduced vulnerability, documented in the assignment design
report:

    The application verifies that the authenticated user holds the
    'loan_officer' ROLE, but does NOT verify that the requested application
    belongs to that user's BRANCH. This is a textbook Broken Object Level
    Authorization (BOLA) weakness (OWASP API1:2023).

Do not deploy this application anywhere except the isolated lab network.
No real customer data, real credentials, or production dependencies are
used anywhere in this file.
"""
import hashlib
import os
import sqlite3
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "training-lab-secret-key-change-me")

DB_PATH = os.environ.get("LOAN_DB_PATH", "loan_portal.db")
STAGE3_FLAG = os.environ.get("STAGE3_FLAG", "NXB{S03_DEV_PLACEHOLDER}")

VULNERABLE_APPLICATION_ID = "APP-0842"  # the seeded cross-branch target


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def pw_hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET"])
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = get_db()
        row = db.execute(
            "SELECT * FROM accounts WHERE username = ?", (username,)
        ).fetchone()
        if row and row["password_hash"] == pw_hash(password):
            session["username"] = row["username"]
            session["role"] = row["role"]
            session["branch"] = row["branch"]
            return redirect(url_for("dashboard"))
        error = "Invalid credentials."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    # Dashboard intentionally only LISTS the officer's own branch applications -
    # the vulnerability is specifically in the direct-reference detail route below.
    apps = db.execute(
        "SELECT application_id, owning_branch, amount_requested FROM applications "
        "WHERE owning_branch = ? ORDER BY application_id",
        (session["branch"],),
    ).fetchall()
    return render_template("dashboard.html", apps=apps, username=session["username"],
                            branch=session["branch"])


@app.route("/application/<application_id>")
@login_required
def view_application(application_id):
    """
    --- INTENTIONAL VULNERABILITY (Stage 3 / BOLA) ---
    This route checks session["role"] == "loan_officer" (AUTHENTICATION +
    coarse role check) but never verifies that `application_id` belongs to
    session["branch"] (missing OBJECT-level AUTHORIZATION check).
    A corrected version would add:
        if row["owning_branch"] != session["branch"]: abort(403)
    """
    if session.get("role") != "loan_officer":
        return render_template("application.html", error="Forbidden: role check failed."), 403

    db = get_db()
    row = db.execute(
        "SELECT * FROM applications WHERE application_id = ?", (application_id,)
    ).fetchone()
    if row is None:
        return render_template("application.html", error="Application not found."), 404

    # NOTE: no branch-ownership comparison happens here - this is the bug.
    cross_branch = row["owning_branch"] != session["branch"]
    flag = None
    if cross_branch and application_id == VULNERABLE_APPLICATION_ID:
        flag = STAGE3_FLAG

    return render_template(
        "application.html",
        app=row,
        cross_branch=cross_branch,
        flag=flag,
        viewer_branch=session["branch"],
    )


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
