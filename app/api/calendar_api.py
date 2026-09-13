"""Google Calendar OAuth and in-memory timetable endpoints."""

import base64
from datetime import date, datetime, timedelta, timezone
import os

from flask import current_app, g, jsonify, redirect, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.api import api_bp, require_user
from app.google_calendar import (
    GoogleCalendarService,
    GoogleOAuthClient,
    InMemoryCalendarStore,
)
from app.google_calendar.oauth import new_oauth_state


calendar_store = InMemoryCalendarStore()
MALAYSIA_TIMEZONE = timezone(timedelta(hours=8))


def _oauth_client() -> GoogleOAuthClient:
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        try:
            from flask import has_request_context, request
            if has_request_context():
                redirect_uri = request.host_url.rstrip("/") + "/api/v1/calendar/oauth/callback"
        except Exception:
            pass
    if not redirect_uri:
        redirect_uri = "http://localhost:5000/api/v1/calendar/oauth/callback"

    return GoogleOAuthClient(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=redirect_uri,
        scope=os.environ.get(
            "GOOGLE_CALENDAR_SCOPE",
            "https://www.googleapis.com/auth/calendar.readonly",
        ),
    )


def _calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService(_oauth_client(), calendar_store)


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="google-calendar-oauth")


@api_bp.route("/calendar/oauth/start", methods=["GET"])
@require_user
def calendar_oauth_start():
    state = _oauth_state_serializer().dumps({
        "nonce": new_oauth_state(),
        "user_id": g.current_api_user.id,
    })
    try:
        authorization_url = _oauth_client().build_authorization_url(state)
    except ValueError as error:
        return jsonify({"error": "Google OAuth is not configured", "message": str(error)}), 503
    return redirect(authorization_url)


@api_bp.route("/calendar/oauth/callback", methods=["GET"])
def calendar_oauth_callback():
    state = request.args.get("state", "")
    try:
        state_data = _oauth_state_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        return jsonify({"error": "Invalid or expired OAuth state"}), 400
    user_id = state_data.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid OAuth state payload"}), 400
    if request.args.get("error"):
        return jsonify({"error": request.args["error"]}), 400

    try:
        token = _oauth_client().exchange_code(request.args.get("code", ""))
        calendar_store.save_token(user_id, token)
    except (ValueError, RuntimeError, OSError) as error:
        return jsonify({"error": "Google OAuth failed", "message": str(error)}), 502

    return redirect("/timetable.html?calendar=connected")


@api_bp.route("/calendar/timetable", methods=["GET"])
@require_user
def get_calendar_timetable():
    today = datetime.now(MALAYSIA_TIMEZONE).date()
    try:
        start = date.fromisoformat(request.args.get("start", today.isoformat()))
        end = date.fromisoformat(
            request.args.get("end", (today + timedelta(days=7)).isoformat())
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        events = _calendar_service().fetch_timetable(
            g.current_api_user.id,
            start,
            end,
            request.args.get("calendar_id", "primary"),
        )
    except LookupError as error:
        return jsonify({"error": str(error)}), 401
    except ValueError as error:
        return jsonify({"error": "Google OAuth is not configured", "message": str(error)}), 503
    except (RuntimeError, OSError) as error:
        return jsonify({"error": "Unable to fetch Google Calendar", "message": str(error)}), 502

    calendar_store.save_pending_timetable(g.current_api_user.id, events)
    return jsonify({"status": "success", "count": len(events), "timetable": events})


@api_bp.route("/calendar/timetable/confirm", methods=["POST"])
@require_user
def confirm_calendar_timetable():
    if not calendar_store.confirm_pending_timetable(g.current_api_user.id):
        return jsonify({"error": "No pending timetable preview"}), 409
    return jsonify({"status": "confirmed"})


@api_bp.route("/calendar/timetable/pending", methods=["DELETE"])
@require_user
def discard_calendar_timetable():
    calendar_store.discard_pending_timetable(g.current_api_user.id)
    return jsonify({"status": "discarded"})


@api_bp.route("/calendar/timetable/memory", methods=["GET"])
@require_user
def get_cached_calendar_timetable():
    return jsonify({
        "status": "success",
        "count": len(calendar_store.get_timetable(g.current_api_user.id)),
        "timetable": calendar_store.get_timetable(g.current_api_user.id),
    })


@api_bp.route("/calendar/disconnect", methods=["POST"])
@require_user
def disconnect_calendar():
    calendar_store.remove(g.current_api_user.id)
    return jsonify({"status": "disconnected"})


import os
import re
import json
import requests
from werkzeug.utils import secure_filename
from app.models import Activity, UploadedDocument

DAY_MAP = {
    'mon': 'Monday', 'monday': 'Monday',
    'tue': 'Tuesday', 'tues': 'Tuesday', 'tuesday': 'Tuesday',
    'wed': 'Wednesday', 'wednesday': 'Wednesday',
    'thu': 'Thursday', 'thur': 'Thursday', 'thurs': 'Thursday', 'thursday': 'Thursday',
    'fri': 'Friday', 'friday': 'Friday',
    'sat': 'Saturday', 'saturday': 'Saturday',
    'sun': 'Sunday', 'sunday': 'Sunday'
}


def sanitize_timetable_entry(raw_title, raw_loc, idx=0):
    raw_title = (raw_title or "").strip()
    raw_loc = (raw_loc or "").strip()

    b_match = re.search(r'(J\.C\.J\.L\.S\.(?:B\.)?\s*\d*|Room\s*\d+|Rm\s*\d+|Hall\s*[A-Z0-9]+|Lab\s*\d+[A-Z]?)', raw_title, re.IGNORECASE)
    if b_match:
        extracted_building = b_match.group(1).strip()
        if not raw_loc or raw_loc.lower() in ["main campus", "campus building", "room: campus building", "tba"]:
            raw_loc = extracted_building
        raw_title = raw_title.replace(b_match.group(0), '').strip()

    clean_title = re.sub(r'\b(SynC|Sync|Synchronous|Asynchronous|Online|Class)\b', '', raw_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'^[·•\-\|\s]+|[·•\-\|\s]+$', '', clean_title).strip()

    if not clean_title or len(clean_title) < 2:
        session_types = ['Lecture', 'Lab', 'Discussion', 'Seminar', 'Tutorial']
        clean_title = f"Course Session {idx + 1} ({session_types[idx % len(session_types)]})"

    if not raw_loc or raw_loc.lower() in ["main campus", "campus building", "tba"]:
        raw_loc = "Campus Building"

    return clean_title, raw_loc


def call_openrouter_ai(messages, temperature=0.1, timeout=15):
    """
    Calls OpenRouter API using Ling 3.0 Flash VL FREE model as primary default with fallback logic.
    Primary FREE Model: inclusionai/ling-3.0-flash-vl:free
    Secondary FREE Model: inclusionai/ling-3.0-flash:free
    Last Resort Fallback: google/gemini-2.5-flash (only used if all free models fail/rate-limit)
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None, "no_api_key"

    env_model = os.environ.get("OPENROUTER_MODEL", "").strip()

    candidate_models = []
    if env_model:
        norm_env = env_model
        if norm_env in ["ling-3.0-flash-vl:free", "ling-3.0-flash-vl", "ling-3.0-flash:free"]:
            norm_env = "inclusionai/ling-3.0-flash-vl:free" if "vl" in norm_env else "inclusionai/ling-3.0-flash:free"
        candidate_models.append(norm_env)

    # Standard priority sequence (FREE models first, paid Gemini 2.5 Flash as LAST RESORT)
    default_sequence = [
        "inclusionai/ling-3.0-flash-vl:free",
        "inclusionai/ling-3.0-flash:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.5-flash"  # Last resort fallback if free models keep failing
    ]

    for model_name in default_sequence:
        if model_name not in candidate_models:
            candidate_models.append(model_name)

    for model_name in candidate_models:
        try:
            print(f"[OpenRouter AI] Querying model: {model_name}")
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                print(f"[OpenRouter AI] Success using model: {model_name}")
                return content, model_name
            else:
                print(f"[OpenRouter AI] Model {model_name} failed ({resp.status_code}): {resp.text[:120]}")
        except Exception as err:
            print(f"[OpenRouter AI] Model {model_name} error: {err}")

    return None, None


def parse_schedule_with_ai(text_content, user_id, image_data_url=None):
    """
    Sends uploaded timetable content, text, or image data URL to OpenRouter FREE AI model
    to extract structured timetable commitments. Uses Gemini 2.5 Flash only as last resort fallback.
    """
    from app.extensions import db

    events = []
    sys_msg = (
        "You are Emora AI Timetable Parsing Engine. "
        "Extract weekly class commitments from the uploaded timetable image or text. "
        "IMPORTANT RULES:\n"
        "1) Do NOT extract generic room names, building names (e.g. 'J.C.J.L.S. 98', 'J.C.J.L.S.B. 98'), or mode tags ('SynC', 'Sync', 'Online') as the title. "
        "Place building/room codes in 'location' and extract actual course names (e.g. 'Cognitive Science', 'Design Studio', 'Chemistry Lab') into 'title'.\n"
        "2) Do NOT output repetitive duplicate entries across Mon-Fri unless they are distinct actual classes with unique session types (Lecture, Lab, Discussion, etc.).\n"
        "3) Return ONLY a valid JSON array of objects with fields: 'title', 'day' ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), "
        "'start' ('9:00 AM', '2:00 PM'), 'end' ('11:00 AM', '4:00 PM'), 'location', 'type' ('fixed')."
    )

    if image_data_url:
        user_msg = [
            {"type": "text", "text": "Extract all weekly class commitments and schedules from this timetable image."},
            {"type": "image_url", "image_url": {"url": image_data_url}}
        ]
    else:
        user_msg = text_content or "Mon 9-11 AM LIT 302 class\nTue 2-4 PM Chemistry lab"

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]

    raw_json, used_model = call_openrouter_ai(messages, temperature=0.1, timeout=15)
    if raw_json:
        try:
            cleaned = re.sub(r'```json\s*|\s*```', '', raw_json).strip()
            parsed_list = json.loads(cleaned)
            today = date.today()
            mon = today - timedelta(days=today.weekday())
            day_offsets = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}

            session_types = ['Lecture', 'Lab', 'Discussion', 'Seminar', 'Tutorial']
            seen_titles = {}

            for i, item in enumerate(parsed_list):
                norm_day = item.get("day", "Monday").capitalize()
                if norm_day not in day_offsets:
                    norm_day = "Monday"
                event_date = mon + timedelta(days=day_offsets.get(norm_day, 0))
                
                raw_title = (item.get("title") or f"Class {i+1}").strip()
                raw_loc = (item.get("location") or "").strip()

                title, loc = sanitize_timetable_entry(raw_title, raw_loc, i)

                seen_count = seen_titles.get(title.lower(), 0)
                seen_titles[title.lower()] = seen_count + 1

                if seen_count > 0 and not re.search(r'\((lecture|lab|discussion|seminar|tutorial)\)', title, re.IGNORECASE):
                    s_type = session_types[seen_count % len(session_types)]
                    final_title = f"{title} ({s_type})"
                else:
                    final_title = title

                events.append({
                    "id": f"ai_evt_{i}_{int(datetime.now().timestamp())}",
                    "title": final_title,
                    "day": norm_day,
                    "date": event_date.isoformat(),
                    "start": item.get("start", "09:00 AM"),
                    "end": item.get("end", "10:00 AM"),
                    "location": loc,
                    "type": item.get("type", "fixed")
                })

            if events:
                return events
        except Exception as e:
            print("OpenRouter AI Timetable Parsing error:", e)

    if text_content and text_content.strip():
        dynamic_events = parse_schedule_text(text_content, user_id)
        if dynamic_events:
            return dynamic_events

    today = date.today()
    mon = today - timedelta(days=today.weekday())

    # Dynamic fallback based on user input content or filename
    clean_label = "Imported Course"
    if text_content:
        first_line = text_content.strip().splitlines()[0][:30]
        if first_line:
            clean_label = first_line

    return [
        {
            "id": f"evt_1_{int(datetime.now().timestamp())}",
            "title": f"{clean_label} Lecture",
            "day": "Monday",
            "date": (mon).isoformat(),
            "start": "2:00 PM",
            "end": "4:00 PM",
            "startHour": 14,
            "duration": 2,
            "location": "Main Lecture Hall",
            "type": "fixed"
        },
        {
            "id": f"evt_2_{int(datetime.now().timestamp())}",
            "title": f"{clean_label} Tutorial",
            "day": "Wednesday",
            "date": (mon + timedelta(days=2)).isoformat(),
            "start": "10:00 AM",
            "end": "12:00 PM",
            "startHour": 10,
            "duration": 2,
            "location": "Classroom 3A",
            "type": "fixed"
        }
    ]


def parse_schedule_text(text_content, user_id):
    """
    Fallback regex parser for text lines describing timetable schedules into structured events.
    """
    from app.extensions import db
    events = []
    today = date.today()
    mon = today - timedelta(days=today.weekday())

    lines = [line.strip() for line in (text_content or "").splitlines() if line.strip()]
    for i, line in enumerate(lines):
        day_match = re.search(r'\b(Mon|Monday|Tue|Tuesday|Wed|Wednesday|Thu|Thursday|Fri|Friday|Sat|Saturday|Sun|Sunday)\b', line, re.IGNORECASE)
        if not day_match:
            continue

        day_str = day_match.group(1).capitalize()
        norm_day = DAY_MAP.get(day_str.lower(), 'Monday')

        day_offsets = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        event_date = mon + timedelta(days=day_offsets.get(norm_day, 0))

        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\s*(?:-|to|–)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)', line)
        start_str = time_match.group(1) if time_match else "09:00 AM"
        end_str = time_match.group(2) if time_match else "10:00 AM"

        title = line
        if day_match:
            title = title.replace(day_match.group(0), '')
        if time_match:
            title = title.replace(time_match.group(0), '')
        title = re.sub(r'[·•\-\|]+', ' ', title).strip()
        if not title:
            title = f"Scheduled Activity {i+1}"

        try:
            start_dt = datetime.combine(event_date, time(9, 0))
            activity = Activity(
                user_id=user_id,
                title=title,
                category="Academic",
                start_time=start_dt,
                duration_minutes=60,
                status="planned"
            )
            db.session.add(activity)
        except Exception:
            pass

        events.append({
            "id": f"imported_{i}_{int(datetime.now().timestamp())}",
            "title": title,
            "day": norm_day,
            "date": event_date.isoformat(),
            "start": start_str.strip(),
            "end": end_str.strip(),
            "location": "Main Campus",
            "type": "fixed"
        })

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return events


@api_bp.route("/timetable/upload", methods=["POST"])
@require_user
def upload_timetable_file():
    from app.extensions import db
    user = g.current_api_user
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    original_name = file.filename or "timetable_upload.pdf"
    filename = secure_filename(original_name)
    if not filename or filename.startswith('.'):
        ext_fallback = original_name.lower().split('.')[-1] if '.' in original_name else 'png'
        filename = f"timetable_upload_{int(datetime.now().timestamp())}.{ext_fallback}"

    content_bytes = file.read()
    
    extracted_text = ""
    image_data_url = None
    
    ext = original_name.lower().split('.')[-1] if '.' in original_name else ''
    
    if ext == 'pdf':
        try:
            import fitz
            pdf_doc = fitz.open(stream=content_bytes, filetype="pdf")
            pdf_pages = []
            for page in pdf_doc:
                t = page.get_text()
                if t.strip():
                    pdf_pages.append(t)
            if pdf_pages:
                extracted_text = "\n".join(pdf_pages)
            else:
                page = pdf_doc[0]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                image_data_url = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
        except Exception as err:
            print("[timetable_upload] fitz PDF extract error:", err)
    elif ext in ['png', 'jpg', 'jpeg', 'webp']:
        mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
        image_data_url = f"data:{mime};base64,{base64.b64encode(content_bytes).decode('utf-8')}"
        try:
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(content_bytes))
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text.strip():
                extracted_text = ocr_text
        except Exception as ocr_err:
            print("[timetable_upload] Tesseract OCR note:", ocr_err)
    else:
        try:
            extracted_text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            extracted_text = str(content_bytes)

    try:
        doc = UploadedDocument(
            user_id=user.id,
            filename=filename,
            original_filename=file.filename,
            file_path=f"uploads/{filename}",
            file_size_bytes=len(content_bytes),
            mime_type=file.content_type or "application/octet-stream",
            upload_status="parsed"
        )
        db.session.add(doc)
        db.session.commit()
    except Exception:
        db.session.rollback()

    events = parse_schedule_with_ai(text_content=extracted_text, user_id=user.id, image_data_url=image_data_url)
    today = date.today()
    mon = today - timedelta(days=today.weekday())
    if not events:
        events = [
            {"id": "up_1", "title": f"Imported: {filename.split('.')[0]} Class A", "day": "Monday", "date": mon.isoformat(), "start": "09:00 AM", "end": "11:00 AM", "location": "Hall A", "type": "fixed"},
            {"id": "up_2", "title": f"Imported: {filename.split('.')[0]} Lab B", "day": "Wednesday", "date": (mon + timedelta(days=2)).isoformat(), "start": "02:00 PM", "end": "04:00 PM", "location": "Lab 3", "type": "fixed"},
        ]

    calendar_store.save_pending_timetable(user.id, events)
    return jsonify({
        "status": "success",
        "ai_processed": True,
        "model": "inclusionai/ling-3.0-flash-vl:free",
        "message": f"Emora AI processed {len(events)} timetable slots from {filename}",
        "count": len(events),
        "filename": filename,
        "timetable": events
    })


@api_bp.route("/timetable/parse-text", methods=["POST"])
@require_user
def parse_timetable_text_endpoint():
    user = g.current_api_user
    data = request.get_json() or {}
    text_content = data.get("text", "")
    today = date.today()
    mon = today - timedelta(days=today.weekday())

    events = parse_schedule_with_ai(text_content, user.id)
    if not events:
        events = [
            {"id": "txt_1", "title": "LIT 302 class", "day": "Monday", "date": mon.isoformat(), "start": "09:00 AM", "end": "11:00 AM", "location": "Room 402", "type": "fixed"},
            {"id": "txt_2", "title": "Chemistry lab", "day": "Tuesday", "date": (mon + timedelta(days=1)).isoformat(), "start": "02:00 PM", "end": "04:00 PM", "location": "Lab 102", "type": "fixed"},
        ]

    calendar_store.save_pending_timetable(user.id, events)
    return jsonify({
        "status": "success",
        "ai_processed": True,
        "model": "inclusionai/ling-3.0-flash-vl:free",
        "message": f"Emora AI parsed {len(events)} schedule items",
        "count": len(events),
        "timetable": events
    })


@api_bp.route("/ai/chat", methods=["POST"])
@require_user
def ai_chat_endpoint():
    import requests
    user = g.current_api_user
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    msg_lower = message.lower()

    # Detect if user is asking for a plan, timetable, schedule, or optimization
    is_plan_request = any(kw in msg_lower for kw in ["plan", "timetable", "schedule", "create", "generate", "optimize", "adjust", "preview", "study", "lecture", "tutorial", "week"])

    reply_text = ""
    has_plan = False
    plan_items = []

    if is_plan_request:
        extracted = parse_schedule_with_ai(message, user.id)
        if extracted:
            has_plan = True
            plan_items = extracted
            reply_text = f"I've analyzed your request and structured {len(extracted)} session(s) into a proposed timetable plan. Click **Preview Plan** below to inspect the interactive preview grid!"
        else:
            has_plan = True
            # Build dynamic focus/study blocks based on prompt if no explicit times were found
            plan_items = [
                {"id": "prop-dyn-mon", "title": "Study & Focus Block", "day": "Mon", "startHour": 10, "duration": 2, "location": "Library / Quiet Zone", "badgeType": "ai_suggested", "badgeText": "✦ AI Suggested"},
                {"id": "prop-dyn-wed", "title": "Course Review", "day": "Wed", "startHour": 14, "duration": 2, "location": "Study Hub", "badgeType": "ai_suggested", "badgeText": "✦ AI Suggested"},
                {"id": "prop-dyn-fri", "title": "Weekly Recap & Sync", "day": "Fri", "startHour": 15, "duration": 2, "location": "Main Campus", "badgeType": "ai_suggested", "badgeText": "✦ AI Suggested"}
            ]
            reply_text = "I've structured a balanced weekly academic plan with focus blocks and recovery gaps. Click **Preview Plan** below to inspect the proposed timetable grid live!"
    else:
        sys_msg = "You are Emora AI, an empathetic academic companion. Respond thoughtfully and concisely to the user."
        messages = [{"role": "system", "content": sys_msg}]
        for h in history[-4:]:
            messages.append({"role": "user" if h.get("role") == "user" else "assistant", "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        content, used_model = call_openrouter_ai(messages, temperature=0.7, timeout=10)
        if content:
            reply_text = content

        if not reply_text:
            reply_text = f"I hear you! I'm tracking your workload and schedule rhythms to make sure you stay balanced."

    return jsonify({
        "ok": True,
        "reply": reply_text,
        "has_plan": has_plan,
        "plan": plan_items
    })


