# ai_api.py
import os
import re
import json
import google.generativeai as genai

# --- API setup ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    # You can hardcode during dev, but env var is recommended:
    # GOOGLE_API_KEY = "YOUR_KEY_HERE"
    pass

genai.configure(api_key=GOOGLE_API_KEY)

# Model with slightly lower temperature for more structured/consistent output
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0.3,
        "top_p": 0.9,
        "max_output_tokens": 2048,
    },
)

# ---------------------------
# Helpers
# ---------------------------

def _strip_md_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove starting fence line
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        # Remove trailing fence
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()

def _normalize_title(title: str) -> str:
    """Remove numbering and 'Chapter/Lesson' prefixes; trim whitespace."""
    t = title.strip()
    # Remove leading "Chapter 3:", "Lesson 1 -", "Unit 2.", "1) ", "1. ", etc.
    t = re.sub(r"^\s*(chapter|lesson|unit)\s*\d+\s*[:\-\.\)]\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*\d+\s*[:\-\.\)]\s*", "", t)
    # Collapse spaces
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for it in items:
        if it.lower() not in seen:
            seen.add(it.lower())
            out.append(it)
    return out

def _ensure_exact_count(topic: str, titles: list[str], n: int) -> list[str]:
    """Ensure exactly n titles (truncate or top up by asking the model)."""
    titles = [t for t in titles if t]  # remove empties
    if len(titles) > n:
        return titles[:n]
    if len(titles) == n:
        return titles

    # Need more titles -> ask for only the missing count
    need = n - len(titles)
    prompt = (
        "You are expanding a course outline.\n"
        f"Topic: {topic}\n"
        f"Existing chapter titles: {json.dumps(titles)}\n\n"
        f"Return ONLY a JSON array of {need} NEW, DISTINCT, descriptive titles that are not numbered "
        'and do not contain words like "Chapter" or "Lesson".\n'
        "Each title <= 60 chars. No duplicates. No extra prose."
    )
    try:
        resp = model.generate_content(prompt)
        txt = _strip_md_fences(resp.text or "")
        extra = json.loads(txt)
        if isinstance(extra, list):
            extra = [_normalize_title(x) for x in extra if isinstance(x, str)]
            extra = [x for x in extra if x]  # non-empty
            combined = _dedupe_preserve_order(titles + extra)
            return combined[:n] if len(combined) >= n else combined
    except Exception:
        # If topping up fails, just pad with generic-but-descriptive endings
        pass

    # Fallback padding (last resort)
    while len(titles) < n:
        titles.append(f"Advanced {topic} — Part {len(titles)+1}")
    return titles[:n]

# ---------------------------
# Public API
# ---------------------------

def get_courses(topic: str, num_chapters: int = 6) -> dict:
    """
    Ask the model for a structured course:
    {
      "course_name": str,
      "description": str,
      "chapters": [str, ...]  # exactly num_chapters, descriptive, non-numbered
    }
    """
    # Very explicit/strict prompt to prevent "Chapter 1/2/3"
    prompt = f"""
You are creating a course outline.

Topic: "{topic}"

Return ONLY a JSON object with exactly these keys:
- "course_name": a concise, specific title (<= 60 chars).
- "description": 1–2 sentence overview.
- "chapters": an array of exactly {num_chapters} DISTINCT, descriptive chapter titles.

Rules for "chapters":
- Do NOT number them (no "1.", "Chapter 1", etc.).
- Do NOT use words like "Chapter", "Lesson", or "Unit".
- Each title must clearly communicate what the chapter covers.
- Each title <= 60 characters.
- All titles must be different and non-empty.

Example (format only):
{{
  "course_name": "Machine Learning Foundations",
  "description": "An applied intro covering data, models, and evaluation.",
  "chapters": [
    "Problem Framing & Datasets",
    "Linear & Logistic Models",
    "Feature Engineering Essentials",
    "Model Evaluation & Metrics",
    "Regularization & Generalization",
    "Unsupervised Learning Basics"
  ]
}}

Return VALID JSON ONLY. No backticks, no commentary.
    """.strip()

    try:
        resp = model.generate_content(prompt)
        raw = _strip_md_fences((resp.text or "").strip())

        # First attempt to parse as JSON object
        data = json.loads(raw)

        # Validate shape
        course_name = str(data.get("course_name", f"{topic} — Course")).strip()
        description = str(data.get("description", f"A course on {topic}.")).strip()
        chapters = data.get("chapters", [])

        if not isinstance(chapters, list):
            chapters = []

        # Normalize titles
        chapters = [_normalize_title(t) for t in chapters if isinstance(t, str)]
        # Remove "chapter"/"lesson" leftovers and duplicates
        chapters = [t for t in chapters if t and not re.search(r"\bchapter\b|\blesson\b|\bunit\b", t, re.I)]
        chapters = _dedupe_preserve_order(chapters)
        # Ensure exact count
        chapters = _ensure_exact_count(topic, chapters, num_chapters)

        # Final sanity: still generic like "Introduction"? keep but it’s fine, they’re descriptive enough
        return {
            "course_name": course_name if course_name else f"{topic} — Course",
            "description": description if description else f"A course on {topic}.",
            "chapters": chapters,
        }

    except Exception as e:
        # Robust fallback if anything goes wrong
        print("AI (get_courses) error:", e)
        base = [
            "Problem Framing & Data Basics",
            "Core Models & Loss Functions",
            "Feature Engineering Essentials",
            "Model Evaluation & Metrics",
            "Regularization & Generalization",
            "Unsupervised Learning Basics",
        ]
        chapters = _ensure_exact_count(topic, base, num_chapters)
        return {
            "course_name": f"{topic} — Structured Course",
            "description": f"An organized course covering key {topic} concepts.",
            "chapters": chapters,
        }


def get_chapter_content(topic: str, chapter_name: str) -> str:
    """
    Generate detailed content for a chapter within a given course topic.
    """
    prompt = f"""
You are writing a course module. This is NOT a book chapter request.

Course: "{topic}"
Chapter Title: "{chapter_name}"

Write a 400–700 word, well-structured explanation in Markdown with these sections:
- Overview (2–3 sentences)
- Key Concepts (bulleted)
- Worked Example(s) (code or step-by-step if relevant)
- Common Pitfalls
- Summary (2–3 sentences)

Rules:
- Tailor the content to the chapter title.
- Do NOT ask for more context or a book name.
- Do NOT include meta-instructions or disclaimers.
- Use concise, clear language.
    """.strip()

    try:
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        print("AI (get_chapter_content) error:", e)
        return "Content could not be generated at this time." 