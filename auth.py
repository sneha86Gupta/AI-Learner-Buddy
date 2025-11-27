# auth.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")  # Change in production

DB_NAME = "users.db"

# --------------------
# Initialize database tables
# --------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                profession TEXT NOT NULL,
                age INTEGER NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # Courses table with progress column
        c.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                course_name TEXT NOT NULL,
                description TEXT,
                num_chapters INTEGER NOT NULL DEFAULT 6,
                progress REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Chapters table with completed column
        c.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                chapter_name TEXT,
                content TEXT,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id)
            )
        """)

        conn.commit()

# Initialize database tables
init_db()

# --------------------
# Login route
# --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            row = c.fetchone()

            if row and check_password_hash(row[1], password):
                session['user_id'] = row[0]  # Save user_id in session
                flash("✅ Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("❌ Invalid username or password!", "danger")
    
    return render_template("login.html")

# --------------------
# Register route
# --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        name = request.form["name"].strip()
        profession = request.form["profession"].strip()
        age = request.form["age"].strip()
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO users (username, email, name, profession, age, password)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, email, name, profession, age, hashed_pw))
                conn.commit()
            flash("✅ Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("❌ Username already exists!", "danger")
    
    return render_template("register.html")

# --------------------
# Logout route
# --------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out!", "info")
    return redirect(url_for("login"))
