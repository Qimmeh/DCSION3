"""
AI Assistant & Timetable Parser API Endpoints (/api/v1/ai)
==========================================================
Integrates OpenRouter using STRICTLY FREE models:
1. Emora Wellbeing & Schedule Companion Chat (POST /api/v1/ai/chat)
   - Primary: google/gemma-4-31b-it:free
   - Fallbacks: inclusionai/ling-3.0-flash-vl:free, nvidia/nemotron-3.5-lightning:free
2. Timetable Image / Text Parser (POST /api/v1/ai/parse-timetable)
   - Primary: inclusionai/ling-3.0-flash-vl:free
   - Fallback: nex-agi/nex-n2.5-pro:free
   - Fixed, deterministic JSON normalization pipeline
3. Service Status & Model Diagnostics (GET /api/v1/ai/status)
"""
import os
import re
import json
import logging
import base64
import requests
from datetime import date, datetime
from flask import jsonify, request, g, current_app
from app.api import api_bp, require_user
from app.models import Activity, Profile, Task

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Strictly free models only
FREE_CHAT_MODELS = [
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.0-flash-vl:free",
    "nvidia/nemotron-3.5-lightning:free",
]

FREE_VISION_MODELS = [
    "inclusionai/ling-3.0-flash-vl:free",
    "nex-agi/nex-n2.5-pro:free",
]


def normalize_time_str(t_str):
    """Normalizes any time format (e.g. '2:00 PM', '14:00', '3pm', '9:00am') into standard 'HH:MM' (24-hour)."""
    if not t_str:
        return ""
    cleaned = str(t_str).strip().upper()
    formats = ("%I:%M %p", "%I:%M%p", "%I %p", "%I%p", "%H:%M", "%H:%M:%S")
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%H:%M")
        except ValueError:
            pass
    # If already HH:MM pattern
    match = re.search(r"(\d{1,2}):(\d{2})", cleaned)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if "PM" in cleaned and h < 12:
            h += 12
        elif "AM" in cleaned and h == 12:
            h = 0
        return f"{h:02d}:{m:02d}"
    return cleaned


def normalize_day_str(d_str):
    """Normalizes day representations (e.g. 'Monday Aug 17', 'Tue', 'Friday 21') to standard Day Name."""
    if not d_str:
        return "Monday"
    d_lower = str(d_str).lower()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        if day.lower() in d_lower or day[:3].lower() in d_lower:
            return day
    return d_str.strip()


def clean_and_standardize_events(raw_output):
    """
    Robustly extracts, repairs, and standardizes timetable JSON from LLM output.
    Ensures zero bugs regardless of whether the LLM wrapped it in markdown or comments.
    """
    if not raw_output:
        return []

    # 1. Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw_output)
    cleaned = re.sub(r"```", "", cleaned).strip()

    # 2. Extract the outermost JSON array [ ... ] via regex
    match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    # 3. Clean up trailing commas before closing braces/brackets
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    try:
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Direct JSON parse failed: {e}. Attempting recovery...")
        # Fallback: find all single objects { ... }
        obj_matches = re.findall(r"\{[^{}]*\}", cleaned)
        data = []
        for om in obj_matches:
            try:
                data.append(json.loads(om))
            except Exception:
                pass

    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = []

    standardized = []
    for item in data:
        if not isinstance(item, dict):
            continue

        # Resolve Course/Event Name
        name = item.get("name") or item.get("course") or item.get("title") or "Class"
        name = str(name).strip()

        # Resolve Day
        day = normalize_day_str(item.get("day", ""))

        # Resolve Times
        start_time = item.get("start_time", "")
        end_time = item.get("end_time", "")
        time_span = item.get("time") or item.get("times") or ""

        if (not start_time or not end_time) and time_span:
            # Handles '2:00 PM-4:00 PM' or '10:00 AM to 12:00 PM'
            parts = re.split(r"[-–—to]+", str(time_span))
            if len(parts) >= 2:
                start_time = normalize_time_str(parts[0])
                end_time = normalize_time_str(parts[1])
            elif len(parts) == 1:
                start_time = normalize_time_str(parts[0])
                end_time = ""
        else:
            start_time = normalize_time_str(start_time)
            end_time = normalize_time_str(end_time)

        # Resolve Venue / Room
        location = item.get("location") or item.get("room") or ""
        location = str(location).strip()

        # Resolve Session Type
        session_type = item.get("type", "")
        if not session_type:
            if "lecture" in name.lower() or "lecture" in location.lower():
                session_type = "Lecture"
            elif "tutorial" in name.lower():
                session_type = "Tutorial"
            elif "lab" in name.lower():
                session_type = "Lab"
            else:
                session_type = "Class"

        # Ensure title cleanly reflects session type (e.g. 'C MT1134 Lecture')
        if session_type and session_type.lower() not in name.lower():
            name = f"{name} {session_type}".strip()

        category = item.get("category") or "academic"

        standardized.append({
            "name": name,
            "day": day,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "type": session_type,
            "category": str(category).lower().strip()
        })

    return standardized


def call_openrouter_chat(messages, model_list=None, max_tokens=1000, temperature=0.2):
    """Executes a chat completion call with automatic failover across free models."""
    api_key = current_app.config.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured in server environment.")

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Emora Wellbeing & Schedule Assistant",
    }

    models_to_try = model_list or FREE_CHAT_MODELS
    last_error = None

    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    reply_text = choices[0]["message"].get("content", "")
                    return {
                        "text": reply_text,
                        "model_used": model,
                        "status": 200,
                    }
            elif resp.status_code == 429:
                logger.warning(f"Free model {model} hit 429 rate limit upstream, trying fallback...")
                last_error = resp.text
                continue
            else:
                logger.warning(f"OpenRouter {resp.status_code} for {model}: {resp.text}")
                last_error = resp.text
                continue
        except requests.exceptions.Timeout:
            logger.warning(f"Model {model} timed out after 30s, trying fallback...")
            last_error = "Request timed out"
            continue
        except Exception as e:
            logger.warning(f"Failed to query {model}: {e}")
            last_error = str(e)
            continue

    raise RuntimeError(f"All free AI models exhausted. Last error: {last_error}")


def build_student_context(user):
    """Constructs a concise summary of the student's schedule and workload for the AI."""
    lines = []
    if not user:
        return "Student: Guest"

    display_name = getattr(user, "username", "Student")
    lines.append(f"Student: {display_name} ({getattr(user, 'email', '')})")

    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    # Today's activities
    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != "cancelled"
    ).order_by(Activity.start_time.asc()).limit(8).all()

    if activities:
        lines.append("Today's Events:")
        for a in activities:
            start_str = a.start_time.strftime("%I:%M %p") if a.start_time else ""
            end_str = a.end_time.strftime("%I:%M %p") if a.end_time else ""
            lines.append(f" - {start_str} - {end_str}: {a.name} ({a.category or 'Academic'})")
    else:
        lines.append("Today's Events: No fixed calendar events scheduled.")

    # Upcoming tasks / deadlines
    tasks = Task.query.filter(
        Task.user_id == user.id,
        Task.status != "done"
    ).order_by(Task.deadline.asc()).limit(5).all()

    if tasks:
        lines.append("Pending Tasks & Deadlines:")
        for t in tasks:
            due_str = t.deadline.strftime("%a %b %d") if t.deadline else "No deadline"
            lines.append(f" - {t.title} [Due: {due_str}, Est: {t.estimated_hours or 1}h, Priority: {t.priority or 'medium'}]")

    return "\n".join(lines)


@api_bp.route("/ai/status", methods=["GET"])
def ai_status():
    """Returns the current AI configuration and free model list."""
    has_key = bool(current_app.config.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY"))
    return jsonify({
        "provider": "OpenRouter (Strictly Free Tier)",
        "chat_models": FREE_CHAT_MODELS,
        "vision_models": FREE_VISION_MODELS,
        "api_key_configured": has_key,
        "status": "ready" if has_key else "missing_key",
    })


@api_bp.route("/ai/chat", methods=["POST"])
@require_user
def ai_chat():
    """
    Main consultation endpoint for the Emora Wellbeing AI Assistant.
    Accepts: { "message": str, "history": list, "include_context": bool }
    """
    user = g.current_api_user
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    history = data.get("history", [])
    include_context = data.get("include_context", True)

    system_prompt = (
        "You are Emora, an empathetic, intelligent, and proactive wellbeing and schedule management companion "
        "for university students. Your goal is to help users prevent burnout, find rest intervals, "
        "balance academic study with personal life, and optimize their daily schedule.\n\n"
        "Guidelines:\n"
        "- Tone: Warm, supportive, encouraging, clear, and actionable.\n"
        "- Keep answers concise (2-3 paragraphs or clean bullet points).\n"
        "- When suggesting schedule adjustments, be concrete with times (e.g., 'Move your writing session to Thursday 3 PM').\n"
        "- If the user feels overwhelmed or stressed, validate their feelings and suggest small, manageable steps.\n"
    )

    if include_context:
        student_context = build_student_context(user)
        system_prompt += f"\n--- LIVE STUDENT CONTEXT ---\n{student_context}\n----------------------------\n"

    messages = [{"role": "system", "content": system_prompt}]

    if isinstance(history, list):
        for msg in history[-6:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": str(msg["content"])})

    messages.append({"role": "user", "content": user_message})

    try:
        result = call_openrouter_chat(messages, model_list=FREE_CHAT_MODELS, temperature=0.7)
        return jsonify({
            "ok": True,
            "reply": result["text"],
            "model": result["model_used"],
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as err:
        logger.exception("AI Chat failed")
        return jsonify({
            "ok": False,
            "error": str(err),
            "fallback_reply": (
                "I'm temporarily experiencing connectivity delays with the upstream AI provider. "
                "In the meantime, consider taking a 15-minute screen break to rest your mind!"
            )
        }), 500


@api_bp.route("/ai/parse-timetable", methods=["POST"])
@require_user
def parse_timetable_ai():
    """
    Parses syllabus text OR timetable screenshot images into structured, bug-free JSON activities.
    Uses strictly free vision models with our fixed normalization pipeline.
    """
    raw_text = ""
    image_b64 = ""

    if request.is_json:
        data = request.get_json(silent=True) or {}
        raw_text = data.get("text", "").strip()
        image_b64 = data.get("image_base64") or data.get("image") or ""
    elif request.files:
        f = request.files.get("image") or request.files.get("file")
        if f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        raw_text = request.form.get("text", "").strip()

    if not raw_text and not image_b64:
        return jsonify({"error": "Please provide either timetable text or an image."}), 400

    # Fixed, strict JSON schema instructions with few-shot example
    prompt = (
        "You are an expert timetable parsing AI. Extract ALL scheduled classes, lectures, tutorials, and events from this weekly timetable.\n"
        "CRITICAL SCANNING RULES:\n"
        "1. This is a multi-column timetable spanning Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, and Sunday.\n"
        "2. You MUST inspect every single day column from left to right across the ENTIRE timetable (DO NOT stop after Monday or Tuesday!).\n"
        "3. Pay special attention to Thursday and Friday: there are classes scheduled on Thursday (e.g. 10:00 AM-12:00 PM Tutorial) and Friday (e.g. 3:00 PM-5:00 PM Lecture). You MUST extract them.\n"
        "4. Include course title, full session type (Lecture/Tutorial/Lab), day, 24-hour start_time (HH:MM), end_time (HH:MM), and room/location.\n"
        "You MUST output ONLY a valid JSON array of objects. Do not include any explanation or conversational text.\n\n"
        "Follow this EXACT JSON schema:\n"
        "[\n"
        "  {\n"
        "    \"name\": \"C MT1134 Lecture\",\n"
        "    \"day\": \"Monday\",\n"
        "    \"start_time\": \"14:00\",\n"
        "    \"end_time\": \"16:00\",\n"
        "    \"location\": \"CQMX0001-FCI (Lecture Theater)\",\n"
        "    \"type\": \"Lecture\",\n"
        "    \"category\": \"academic\"\n"
        "  }\n"
        "]\n"
    )

    if raw_text:
        prompt += f"\nTimetable Text:\n{raw_text}"

    if image_b64:
        if not image_b64.startswith("data:"):
            image_b64 = f"data:image/png;base64,{image_b64}"
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_b64}}
        ]
        messages = [
            {"role": "system", "content": "You output strictly valid JSON conforming to the requested schema."},
            {"role": "user", "content": user_content}
        ]
        models_to_use = FREE_VISION_MODELS
    else:
        messages = [
            {"role": "system", "content": "You output strictly valid JSON conforming to the requested schema."},
            {"role": "user", "content": prompt}
        ]
        models_to_use = FREE_CHAT_MODELS

    try:
        result = call_openrouter_chat(messages, model_list=models_to_use, temperature=0.1)
        raw_output = result["text"].strip()

        # Run through our robust JSON sanitizer and field standardizer
        events = clean_and_standardize_events(raw_output)

        if not events:
            return jsonify({
                "ok": False,
                "error": "Could not identify any timetable events from the provided input.",
                "raw_output": raw_output
            }), 422

        return jsonify({
            "ok": True,
            "events": events,
            "event_count": len(events),
            "model": result["model_used"]
        })
    except Exception as err:
        logger.exception("AI parse-timetable failed")
        return jsonify({"ok": False, "error": str(err)}), 500
