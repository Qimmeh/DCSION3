import os
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from huggingface_hub import InferenceClient

from app.extensions import db, csrf
from app.models import JournalEntry

bp = Blueprint("journal", __name__, url_prefix="/journal")
load_dotenv()
# Fallback emotion keyword dictionary if HF API token is missing or request fails
LEXICON = {
    "joy": ["happy", "joy", "great", "awesome", "good", "love", "relaxed", "peaceful", "proud"],
    "sadness": ["sad", "depressed", "unhappy", "lonely", "hopeless", "crying", "miserable", "drained"],
    "anger": ["angry", "mad", "furious", "annoyed", "irritated", "hate", "frustrated"],
    "fear": ["scared", "afraid", "anxious", "terrified", "panic", "nervous", "worried", "stressed"],
    "disgust": ["disgusted", "revolted", "sick", "gross", "nauseous"]
}


def fallback_emotion(text):
    """Simple keyword matching fallback when HuggingFace API is unavailable."""
    words = text.lower().split()
    scores = {e: 0 for e in LEXICON}
    for w in words:
        for emotion, keywords in LEXICON.items():
            if w in keywords:
                scores[emotion] += 1
    top_emotion = max(scores, key=scores.get)
    return top_emotion if scores[top_emotion] > 0 else "joy"


@bp.route("/emotion", methods=["POST"])
@csrf.exempt
def analyze_emotion():
    """Receives text payload and returns classified emotion scores using HuggingFace InferenceClient."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"ok": False, "error": "No text content provided"}), 400

    token = os.environ.get("HF_TOKEN")

    if not token:
        emotion = fallback_emotion(text)
        return jsonify({
            "ok": True,
            "source": "fallback_lexicon",
            "top_emotion": emotion,
            "scores": [{"label": emotion, "score": 1.0}]
        })

    try:
        client = InferenceClient(
            provider="auto",
            api_key=token,
        )

        results = client.text_classification(
            text,
            model="bhadresh-savani/distilbert-base-uncased-emotion",
        )

        parsed_results = []
        for item in results:
            label = getattr(item, "label", None) or (item.get("label") if isinstance(item, dict) else str(item))
            score = getattr(item, "score", None) or (item.get("score") if isinstance(item, dict) else 0.0)

            clean_label = label.lower()
            parsed_results.append({"label": clean_label, "score": round(float(score), 4)})

        parsed_results.sort(key=lambda x: x["score"], reverse=True)
        top_emotion = parsed_results[0]["label"] if parsed_results else "joy"

        return jsonify({
            "ok": True,
            "source": "huggingface",
            "top_emotion": top_emotion,
            "scores": parsed_results
        })

    except Exception as err:
        emotion = fallback_emotion(text)
        return jsonify({
            "ok": True,
            "source": "fallback_error",
            "scores": [{"label": emotion, "score": 1.0}]
        })


@bp.route("/entries", methods=["GET"])
def get_journal_entries():
    """Retrieves all saved journal entries from database."""
    if current_user.is_authenticated:
        entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).all()
    else:
        entries = JournalEntry.query.order_by(JournalEntry.created_at.desc()).all()

    return jsonify({
        "ok": True,
        "entries": [e.to_dict() for e in entries]
    })


@bp.route("/entries", methods=["POST"])
@csrf.exempt
def save_journal_entry():
    """Saves a new reflection entry to database."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    emotion = data.get("emotion", "joy")

    if not text:
        return jsonify({"ok": False, "error": "No content provided"}), 400

    user_id = current_user.id if current_user.is_authenticated else None

    entry = JournalEntry(
        user_id=user_id,
        content=text,
        top_emotion=emotion
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({
        "ok": True,
        "entry": entry.to_dict()
    }), 201


if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(bp)
    sample = [
        "It's a rough day to go by",
        "The results are so unfair, how can the score on the scoreboard be manipulated",
        "It's a fine day, a perfect day for work",
        ]
    with app.test_client() as client:
        for text in sample:
            response = client.post("/journal/emotion", json={"text": text})
            print(response.status_code)
            print(response.get_json())