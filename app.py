# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from functools import wraps
from auth import app, DB_NAME  # Using app & DB_NAME from auth.py
from ai_api import get_chapter_content, get_courses

# --------------------
# Prevent caching of authenticated pages
# --------------------
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# --------------------
# Login required decorator
# --------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("⚠️ Please log in first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# --------------------
# Home route → main.html
# --------------------
@app.route("/")
def main():
    return render_template("main.html")

# --------------------
# Dashboard route: show courses & AI prompt
# --------------------
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user_id = session["user_id"]

    # Add new course
    if request.method == "POST":
        course_name = request.form.get("course_name")
        num_chapters = request.form.get("num_chapters", type=int) or 6
        level = request.form.get("level") or "Beginner"

        if course_name:
            course_data = get_courses(f"{course_name} ({level})", num_chapters)

            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                # Save course
                c.execute(
                    "INSERT INTO courses (user_id, course_name, description, num_chapters) VALUES (?, ?, ?, ?)",
                    (user_id, course_data["course_name"], course_data["description"], num_chapters)
                )
                course_id = c.lastrowid

                # Save generated chapters
                for chapter_title in course_data["chapters"]:
                    c.execute(
                        "INSERT INTO chapters (course_id, chapter_name, content, completed) VALUES (?, ?, ?, 0)",
                        (course_id, chapter_title, "")
                    )

                conn.commit()

            flash("✅ Course and chapters generated successfully!", "success")
            return redirect(url_for("dashboard"))

    # Fetch courses with progress
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, course_name, description FROM courses WHERE user_id=?",
            (user_id,)
        )
        courses = c.fetchall()

        # Compute progress for each course based on chapters
        courses_with_progress = []
        for course in courses:
            course_id = course[0]
            c.execute("SELECT COUNT(*) FROM chapters WHERE course_id=?", (course_id,))
            total = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM chapters WHERE course_id=? AND completed=1", (course_id,))
            completed = c.fetchone()[0] or 0
            progress = int((completed / total) * 100) if total > 0 else 0
            courses_with_progress.append({
                "id": course[0],
                "course_name": course[1],
                "description": course[2],
                "progress": progress
            })

    return render_template("dashboard.html", courses=courses_with_progress, user_id=user_id)

# --------------------
# Chapters page
# --------------------
@app.route("/chapters/<int:course_id>")
@login_required
def chapters(course_id):
    user_id = session["user_id"]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Verify course ownership
        c.execute(
            "SELECT id, course_name, description FROM courses WHERE id=? AND user_id=?",
            (course_id, user_id)
        )
        course = c.fetchone()
        if not course:
            flash("❌ Course not found or access denied.", "danger")
            return redirect(url_for("dashboard"))

        c.execute("SELECT id, chapter_name, completed FROM chapters WHERE course_id=?", (course_id,))
        chapters = c.fetchall()

    return render_template("chapters.html", course=course, chapters=chapters)

# --------------------
# Chapter content page
# --------------------
@app.route("/content/<int:chapter_id>")
@login_required
def content(chapter_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Fetch chapter
        c.execute("SELECT chapter_name, content, course_id, completed FROM chapters WHERE id=?", (chapter_id,))
        chapter = c.fetchone()

        if chapter:
            # Generate content if empty
            if not chapter[1]:
                c.execute("SELECT course_name FROM courses WHERE id=?", (chapter[2],))
                course = c.fetchone()
                topic = course[0] if course else "Unknown Topic"
                generated_content = get_chapter_content(topic, chapter[0])
                c.execute("UPDATE chapters SET content=?, completed=1 WHERE id=?", (generated_content, chapter_id))
                conn.commit()
                chapter = (chapter[0], generated_content, chapter[2], 1)
            elif chapter[3] == 0:
                # Mark as completed if already has content
                c.execute("UPDATE chapters SET completed=1 WHERE id=?", (chapter_id,))
                conn.commit()
                chapter = (chapter[0], chapter[1], chapter[2], 1)

    return render_template("content.html", chapter=chapter)

# --------------------
# Update chapter completion API with real-time dashboard counts
# --------------------
@app.route("/update_chapter", methods=["POST"])
@login_required
def update_chapter():
    chapter_id = request.form.get("chapter_id")
    completed = int(request.form.get("completed"))  # 0 or 1

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Update chapter completion
        c.execute("UPDATE chapters SET completed=? WHERE id=?", (completed, chapter_id))
        
        # Recalculate progress for the course
        c.execute("SELECT course_id FROM chapters WHERE id=?", (chapter_id,))
        course_id = c.fetchone()[0]

        c.execute("SELECT COUNT(*), SUM(completed) FROM chapters WHERE course_id=?", (course_id,))
        total, done = c.fetchone()
        progress = int((done / total) * 100) if total else 0
        c.execute("UPDATE courses SET progress=? WHERE id=?", (progress, course_id))

        # Get real-time completed and in-progress counts for this user
        c.execute("SELECT COUNT(*) FROM courses WHERE user_id=? AND progress=100", (session["user_id"],))
        completed_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM courses WHERE user_id=? AND progress<100", (session["user_id"],))
        inprogress_count = c.fetchone()[0]

        conn.commit()

    # Return progress and updated dashboard counts
    return jsonify({
        "success": True,
        "progress": progress,
        "completed_count": completed_count,
        "inprogress_count": inprogress_count
    })

# --------------------
# About page
# --------------------
@app.route("/about")
def about():
    return render_template("about.html")

# --------------------
# Run Flask app
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
