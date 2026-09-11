"""
AI Assistant & Timetable Parser API Endpoints (/api/v1/ai)
==========================================================
Integrates OpenRouter with Google Gemma 4 31B (Free) to power:
1. Emora Wellbeing & Schedule Companion Chat (POST /api/v1/ai/chat)
2. Timetable Syllabus / Raw Text Parser (POST /api/v1/ai/parse-timetable)
3. Service Status & Model Info (GET /api/v1/ai/status)
"""
import os
import json
import logging
import requests
from datetime import date, datetime
from flask import jsonify, request, g, current_app
from app.api import api_bp, require_user
from app.models import Activity, Profile, Task

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
]


def call_openrouter_chat(messages, preferred_model=None, max_tokens=1000, temperature=0.7):
    """
    Executes a chat completion call to OpenRouter with automatic fallback
    if the preferred model is temporarily rate-limited (HTTP 429).
    """
    api_key = current_app.config.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured in server environment.")

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Emora Wellbeing & Schedule Assistant",
    }

    target_model = preferred_model or current_app.config.get("OPENROUTER_MODEL") or DEFAULT_MODEL
    models_to_try = [target_model] + [m for m in FALLBACK_MODELS if m != target_model]

    last_error = None
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=25)
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
                logger.warning(f"Model {model} hit 429 rate limit upstream, trying fallback...")
                last_error = resp.text
                continue
            else:
                logger.error(f"OpenRouter error {resp.status_code} for {model}: {resp.text}")
                last_error = resp.text
                continue
        except requests.exceptions.Timeout:
            logger.warning(f"Model {model} timed out after 25s, trying fallback...")
            last_error = "Request timed out"
            continue
        except Exception as e:
            logger.error(f"Failed to query {model}: {e}")
            last_error = str(e)
            continue

    raise RuntimeError(f"All AI models exhausted. Last error: {last_error}")


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
    """Returns the current AI configuration and health."""
    has_key = bool(current_app.config.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY"))
    active_model = current_app.config.get("OPENROUTER_MODEL") or DEFAULT_MODEL
    return jsonify({
        "provider": "OpenRouter",
        "configured_model": active_model,
        "available_fallbacks": FALLBACK_MODELS,
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
        "for university students and busy individuals. Your goal is to help users prevent burnout, find rest "
        "intervals, balance academic study with personal life, and optimize their daily schedule.\n\n"
        "Guidelines:\n"
        "- Tone: Warm, supportive, encouraging, clear, and actionable.\n"
        "- Keep answers reasonably concise (2-4 paragraphs max or clean bullet points) so they are easy to read on mobile and desktop.\n"
        "- When suggesting schedule adjustments, be concrete with times (e.g., 'Move your 2-hour writing session to Thursday 3 PM').\n"
        "- If the user feels overwhelmed or stressed, validate their feelings and suggest small, manageable steps.\n"
    )

    if include_context:
        student_context = build_student_context(user)
        system_prompt += f"\n--- LIVE STUDENT CONTEXT ---\n{student_context}\n----------------------------\n"

    messages = [{"role": "system", "content": system_prompt}]

    # Append valid history (up to last 6 messages)
    if isinstance(history, list):
        for msg in history[-6:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": str(msg["content"])})

    messages.append({"role": "user", "content": user_message})

    try:
        preferred_model = current_app.config.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        result = call_openrouter_chat(messages, preferred_model=preferred_model)
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
                "I'm temporarily experiencing connectivity issues with the upstream AI provider. "
                "In the meantime, consider protecting a 30-minute rest buffer between your major tasks today!"
            )
        }), 500


@api_bp.route("/ai/parse-timetable", methods=["POST"])
@require_user
def parse_timetable_ai():
    """
    Parses unstructured syllabus text OR timetable screenshot images into structured JSON activities.
    Accepts:
      JSON: { "text": str } OR { "image_base64": str }
      Multipart: file 'image' / 'file'
    Returns: { "events": [ { "name": ..., "day": ..., "start_time": ..., "end_time": ..., "location": ..., "category": ... } ] }
    """
    import base64
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

    prompt = (
        "You are an expert schedule extraction engine. Extract all classes, lectures, tutorials, "
        "meetings, study blocks, and tasks from the provided timetable input.\n\n"
        "Output ONLY a valid JSON array of objects with no markdown code fences, no preamble, and no explanation.\n"
        "Each object MUST have the following keys:\n"
        "- \"name\": string (e.g. \"C MT1134 Lecture\" or \"C MT1134 Tutorial\")\n"
        "- \"day\": string (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)\n"
        "- \"start_time\": string in HH:MM format (24-hour, e.g. \"09:00\" or \"14:00\")\n"
        "- \"end_time\": string in HH:MM format (24-hour, e.g. \"11:00\" or \"16:00\")\n"
        "- \"location\": string (room or building, e.g. \"CQMX0001-FCI\" or empty string)\n"
        "- \"type\": string (e.g. \"Lecture\", \"Tutorial\", \"Classroom\", \"Lab\")\n"
        "- \"category\": string (one of: \"academic\", \"work\", \"social\", \"health\", \"errands\")\n"
    )

    if raw_text:
        prompt += f"\nRaw Text:\n{raw_text}"

    if image_b64:
        if not image_b64.startswith("data:"):
            image_b64 = f"data:image/png;base64,{image_b64}"
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_b64}}
        ]
        messages = [
            {"role": "system", "content": "You output strictly valid JSON."},
            {"role": "user", "content": user_content}
        ]
        preferred_model = "inclusionai/ling-3.0-flash-vl:free"
    else:
        messages = [
            {"role": "system", "content": "You output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ]
        preferred_model = current_app.config.get("OPENROUTER_MODEL") or DEFAULT_MODEL

    try:
        result = call_openrouter_chat(messages, preferred_model=preferred_model, temperature=0.2)
        raw_output = result["text"].strip()

        # Clean markdown code block fences if present
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`")
            if raw_output.startswith("json"):
                raw_output = raw_output[4:].strip()

        events = json.loads(raw_output)
        return jsonify({
            "ok": True,
            "events": events,
            "model": result["model_used"]
        })
    except json.JSONDecodeError:
        return jsonify({
            "ok": False,
            "error": "Failed to parse structured JSON from AI output",
            "raw_output": raw_output
        }), 502
    except Exception as err:
        logger.exception("AI parse-timetable failed")
        return jsonify({"ok": False, "error": str(err)}), 500

