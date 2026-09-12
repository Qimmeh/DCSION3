import os
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify
from flask_login import current_user
from huggingface_hub import InferenceClient

from app.extensions import csrf

bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")
load_dotenv()

# Map raw HuggingFace emotion labels or keywords to Emora palette keys
EMOTION_MAP = {
    "anger": "angry",
    "angry": "angry",
    "sadness": "bad",
    "sad": "bad",
    "bad": "bad",
    "fear": "anxious",
    "anxious": "anxious",
    "stress": "stressed",
    "stressed": "stressed",
    "tired": "tired",
    "fatigue": "tired",
    "joy": "happy",
    "happy": "happy",
    "love": "grateful",
    "grateful": "grateful",
    "lonely": "lonely",
    "surprise": "happy",
}

LEXICON = {
    "angry": ["angry", "mad", "furious", "pissed", "rage", "irritated", "annoyed", "hate", "frustrated"],
    "anxious": ["anxious", "anxiety", "nervous", "worry", "worried", "scared", "fear", "afraid", "panic", "tense", "dread"],
    "stressed": ["stress", "stressed", "overwhelmed", "burnout", "swamped", "pressure", "hectic"],
    "bad": ["bad", "sad", "down", "unhappy", "terrible", "awful", "crying", "depressed", "hopeless", "hurt", "miserable"],
    "tired": ["tired", "exhausted", "sleepy", "fatigue", "drained", "weary", "sleepless"],
    "lonely": ["lonely", "alone", "isolated", "empty", "abandoned"],
    "grateful": ["love", "grateful", "thankful", "blessed", "appreciate"],
    "happy": ["good", "great", "happy", "energized", "excited", "awesome", "wonderful", "amazing", "motivated"],
    "calm": ["calm", "peace", "peaceful", "relaxed", "serene", "chill", "balanced", "fine", "ok"]
}

EMPATHETIC_RESPONSES = {
    "angry": "I hear your frustration and anger. Taking a step back and giving yourself room to breathe can help release that tension.",
    "anxious": "I notice you're feeling anxious. Take a deep, slow breath—you don't have to tackle everything all at once.",
    "stressed": "Sounds like you're carrying a lot of pressure right now. Let's make sure we protect space for your rest and recovery.",
    "bad": "I'm really sorry you're feeling down. Be gentle with yourself today, and take things one small step at a time.",
    "tired": "You sound genuinely exhausted. Rest is essential—consider pausing for a recovery break or wrapping up early today.",
    "lonely": "Feeling isolated can be heavy. Remember I'm here to support you and lighten your cognitive load.",
    "grateful": "It's wonderful to feel that warmth and gratitude. Celebrating these positive moments keeps us grounded.",
    "happy": "That's great energy! Capitalize on this positive momentum while making sure to keep your rhythm sustainable.",
    "calm": "I'm glad you're feeling balanced and calm. Maintaining a tranquil pace helps sustain long-term focus and wellbeing."
}


def detect_emotion(text, token=None):
    if token:
        try:
            client = InferenceClient(provider="auto", api_key=token)
            results = client.text_classification(text, model="bhadresh-savani/distilbert-base-uncased-emotion")
            if results:
                top = results[0]
                label = getattr(top, "label", None) or (top.get("label") if isinstance(top, dict) else str(top))
                score = getattr(top, "score", None) or (top.get("score") if isinstance(top, dict) else 1.0)
                mapped_label = EMOTION_MAP.get(label.lower(), "calm")
                return mapped_label, float(score)
        except Exception:
            pass

    # Keyword fallback matching
    words = text.lower().split()
    scores = {e: 0 for e in LEXICON}
    for w in words:
        for emotion, keywords in LEXICON.items():
            if w in keywords:
                scores[emotion] += 1
    top_emotion = max(scores, key=scores.get)
    if scores[top_emotion] > 0:
        return top_emotion, 0.85
    return "calm", 0.5


@bp.route("/chat", methods=["POST"])
@csrf.exempt
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"ok": False, "error": "No message provided"}), 400

    token = os.environ.get("HF_TOKEN")
    emotion_label, confidence = detect_emotion(message, token)

    reply_text = None
    if token:
        try:
            client = InferenceClient(provider="auto", api_key=token)
            messages_payload = [
                {
                    "role": "system",
                    "content": (
                        "You are Emora, an empathetic AI companion focused on user wellbeing, workload balancing, "
                        "and recovery guidance. Keep responses concise, warm, supportive, and practical (2-4 sentences max)."
                    )
                }
            ]
            for item in history[-6:]:
                role = item.get("role", "user")
                content = item.get("content", "")
                if content and role in ("user", "assistant"):
                    messages_payload.append({"role": role, "content": content})

            messages_payload.append({"role": "user", "content": message})

            response = client.chat_completion(
                messages=messages_payload,
                model="Qwen/Qwen2.5-Coder-32B-Instruct",
                max_tokens=250,
                temperature=0.7
            )
            if response and response.choices:
                reply_text = response.choices[0].message.content.strip()
        except Exception:
            try:
                response = client.chat_completion(
                    messages=messages_payload,
                    model="meta-llama/Llama-3.2-3B-Instruct",
                    max_tokens=250,
                    temperature=0.7
                )
                if response and response.choices:
                    reply_text = response.choices[0].message.content.strip()
            except Exception:
                pass

    if not reply_text:
        base = EMPATHETIC_RESPONSES.get(emotion_label, EMPATHETIC_RESPONSES["calm"])
        reply_text = f"{base} I'm here to help you optimize your schedule and support your mental space."

    return jsonify({
        "ok": True,
        "reply": reply_text,
        "emotion": {
            "label": emotion_label,
            "score": round(confidence, 4)
        }
    })
