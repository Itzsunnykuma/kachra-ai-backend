from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# --------------------------------
# HF CHAT COMPLETIONS (NO 410)
# --------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://router.huggingface.co/v1/chat/completions"

# BEST WORKING MODEL (no shutdowns)
MODEL = "meta-llama/Llama-3.2-3B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are Kachra 😂 — a funny savage Indian friend. Reply in short Hinglish."
}


# ------------------------------
# ROUTES
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
            "model": MODEL,
            "messages": [
                SYSTEM_PROMPT,
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": 150,
            "temperature": 0.8
        }

        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=40)

        if r.status_code != 200:
            return jsonify({"reply": f"HF error {r.status_code}"}), 500

        out = r.json()
        reply = out["choices"][0]["message"]["content"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed but saved 😅: {e}"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
