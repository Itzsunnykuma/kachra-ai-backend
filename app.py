from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# --------------------------------
# GEMINI API CONFIG
# --------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Updated model to Gemini 2.5 Flash
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

HEADERS = {
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = "You are Kachra 😂 — a funny savage Indian friend. Reply in short Hinglish."


# ------------------------------
# ROUTES
# ------------------------------
@app.route("/")
def home():
    return "Kachra AI (Gemini 2.5 Flash) backend is live!"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_msg = (data.get("message") or "").strip()

        if not user_msg:
            return jsonify({"reply": "Kuch to bol yaar 😄"}), 400

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\nUser: {user_msg}"}
                    ]
                }
            ]
        }

        r = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers=HEADERS,
            json=payload,
            timeout=40
        )

        if r.status_code != 200:
            return jsonify({"reply": f"Gemini error {r.status_code}"}), 500

        out = r.json()

        reply = out["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed but saved 😅: {e}"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
