from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)

# ------------------------------
# Gemini 2.5 Flash config
# ------------------------------
API_KEY = os.getenv("GEMINI_KEY")  # your Gemini API key
MODEL = "gemini-2.5-flash"
API_URL = "https://api.generativeai.google/v1beta2/models/gemini-2.5-flash:generateText"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = "You are Kachra 😂 — a funny savage Indian friend. Reply in short Hinglish."

# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def home():
    return "Kachra AI backend is live!"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_msg = (data.get("message") or "").strip()

        if not user_msg:
            return jsonify({"reply": "Kuch to bol yaar 😄"}), 400

        payload = {
            "prompt": f"{SYSTEM_PROMPT}\nUser: {user_msg}\nKachra:",
            "temperature": 0.8,
            "candidate_count": 1,
            "max_output_tokens": 200
        }

        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=40)
        if r.status_code != 200:
            return jsonify({"reply": f"Gemini error {r.status_code}"}), 500

        out = r.json()
        # Extract the text from Gemini response
        text = out.get("candidates", [{}])[0].get("output", "").strip()
        return jsonify({"reply": text})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed but saved 😅: {e}"}), 200

@app.route("/reset", methods=["POST"])
def reset():
    return jsonify({"message":"Chat reset successfully"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
