from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import time
from typing import Dict, List

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ------------------------------
# HF CONFIG (FIXED ENDPOINT)
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# MEMORY
# ------------------------------
MAX_HISTORY = 8
session_store: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are Kachra 😂, a funny Hinglish chatbot. Reply short, witty, Indian style."
}

# ------------------------------
# HELPERS
# ------------------------------
def clean_text(t):
    if not isinstance(t, str):
        return "Kuch gadbad ho gaya 😅"
    return t.replace("\u0000", "").strip()

def get_session_messages(session_id):
    if session_id not in session_store:
        session_store[session_id] = [SYSTEM_PROMPT.copy()]
    return session_store[session_id]

def trim_history(messages):
    system = messages[:1]
    rest = messages[1:]
    return system + rest[-MAX_HISTORY:]

# ------------------------------
# ROOT
# ------------------------------
@app.route("/")
def home():
    return "Kachra AI backend is live!"

# ------------------------------
# CHAT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        msg = (data.get("message") or "").strip()
        session_id = data.get("session_id") or "anon"

        if not HF_TOKEN:
            return jsonify({"reply": "HF token missing 🤦"}), 500

        if not msg:
            return jsonify({"reply": "Kya bolu? Kuch to likh 😄"}), 400

        # Build conversation history
        messages = get_session_messages(session_id)
        messages.append({"role": "user", "content": msg})
        session_store[session_id] = trim_history(messages)

        # HF expects "inputs" not "messages"
        payload = {
            "inputs": {
                "past_user_inputs": [
                    m["content"] for m in session_store[session_id] if m["role"] == "user"
                ],
                "generated_responses": [
                    m["content"] for m in session_store[session_id] if m["role"] == "assistant"
                ],
                "text": msg
            },
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.75,
                "top_p": 0.9,
            }
        }

        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=45)

        if r.status_code != 200:
            return jsonify({"reply": f"HF error {r.status_code}"}), 500

        out = r.json()

        # HF returns a list of dicts
        reply_text = out[0]["generated_text"] if isinstance(out, list) else out

        reply_text = clean_text(reply_text)

        # Save assistant reply
        messages = get_session_messages(session_id)
        messages.append({"role": "assistant", "content": reply_text})
        session_store[session_id] = trim_history(messages)

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"reply": f"Backend error 😅: {e}"}), 200

# ------------------------------
# RESET
# ------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    sid = (request.get_json(force=True) or {}).get("session_id") or "anon"
    session_store.pop(sid, None)
    return jsonify({"message": "Chat reset!"})

# ------------------------------
# RUN (LOCAL ONLY)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
