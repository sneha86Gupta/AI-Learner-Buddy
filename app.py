from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from auth import app, DB_NAME  # Using app & DB_NAME from auth.py
from ai_api import get_chapter_content


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

    # Fetch courses
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, course_name, description FROM courses WHERE user_id=?",
            (user_id,)
        )
        courses = c.fetchall()

    # Add new course
    if request.method == "POST":
        course_name = request.form.get("course_name")
        num_chapters = request.form.get("num_chapters", type=int) or 6
        level = request.form.get("level") or "Beginner"

        if course_name:
            # Call AI API to generate course & chapters
            from ai_api import get_courses
            course_data = get_courses(f"{course_name} ({level})", num_chapters)
    
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                # Save course
                c.execute(
                    "INSERT INTO courses (user_id, course_name, description) VALUES (?, ?, ?)",
                    (user_id, course_data["course_name"], course_data["description"])
                )
                course_id = c.lastrowid
    
                # Save generated chapters
                for chapter_title in course_data["chapters"]:
                    c.execute(
                        "INSERT INTO chapters (course_id, chapter_name, content) VALUES (?, ?, ?)",
                        (course_id, chapter_title, "")
                    )
    
                conn.commit()
    
            flash("✅ Course and chapters generated successfully!", "success")
            return redirect(url_for("dashboard"))


    return render_template("dashboard.html", courses=courses, user_id=user_id)


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

        c.execute("SELECT id, chapter_name FROM chapters WHERE course_id=?", (course_id,))
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
        c.execute("SELECT chapter_name, content, course_id FROM chapters WHERE id=?", (chapter_id,))
        chapter = c.fetchone()

        if chapter and not chapter[1]:
            # Get course topic
            c.execute("SELECT course_name FROM courses WHERE id=?", (chapter[2],))
            course = c.fetchone()
            topic = course[0] if course else "Unknown Topic"

            generated_content = get_chapter_content(topic, chapter[0])
            c.execute("UPDATE chapters SET content=? WHERE id=?", (generated_content, chapter_id))
            conn.commit()
            chapter = (chapter[0], generated_content, chapter[2])

    return render_template("content.html", chapter=chapter)

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
