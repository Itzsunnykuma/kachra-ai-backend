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
# HF CONFIG
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://api-inference.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# SESSION MEMORY
# ------------------------------
MAX_HISTORY = 8
session_store: Dict[str, List[Dict[str, str]]] = {}

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are a funny Hinglish chatbot named "Kachra 😂".
Talk like an Indian friend – short, witty, savage replies.
""".strip()
}

ASSOCIATE_TAG = "itzsunnykum01-21"

# ------------------------------
# HELPERS
# ------------------------------
def convert_amazon_links_to_affiliate(text: str) -> str:
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace(match):
        url = match.group(0)
        if "tag=" not in url:
            url += ("&" if "?" in url else "?") + f"tag={ASSOCIATE_TAG}"
        name = url.split("/")[-2].replace("-", " ")
        name = re.sub(r"\?.*$", "", name)
        return f'<a href="{url}" target="_blank" rel="noopener">{name}</a>'

    return re.sub(pattern, replace, text)

def clean_text(t):
    if not isinstance(t, str):
        return "Kuch gadbad ho gaya 😅"
    return t.replace("\u0000", "").strip()

def get_session_messages(session_id: str):
    if session_id not in session_store:
        session_store[session_id] = [SYSTEM_PROMPT.copy()]
    return session_store[session_id]

def trim_history(messages):
    """
    Keep system prompt + last MAX_HISTORY user/assistant messages.
    """
    system_prompt = messages[:1]
    rest = messages[1:]
    rest = rest[-MAX_HISTORY:]
    return system_prompt + rest

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

        messages = get_session_messages(session_id)
        messages.append({"role": "user", "content": msg})
        session_store[session_id] = trim_history(messages)

        payload = {
            "model": MODEL,
            "messages": session_store[session_id],
            "max_tokens": 250,
            "temperature": 0.75,
            "top_p": 0.9
        }

        reply_text = None
        backoff = [1, 2, 4]

        for attempt in range(len(backoff) + 1):
            try:
                r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=45)

                if r.status_code in (429, 502, 503):
                    if attempt < len(backoff):
                        time.sleep(backoff[attempt])
                        continue
                    return jsonify({"reply": "HF busy hai 😭 thoda baad aana"}), 503

                if r.status_code != 200:
                    return jsonify({"reply": f"HF error: {r.status_code}"}), 500

                out = r.json()
                if "choices" in out and out["choices"]:
                    choice = out["choices"][0]
                    reply_text = (
                        choice.get("message", {}).get("content")
                        or choice.get("text")
                        or choice.get("generated_text")
                    )

                if not reply_text and "generated_text" in out:
                    reply_text = out["generated_text"]

                if not reply_text:
                    reply_text = str(out)[:500]

                break

            except Exception:
                if attempt < len(backoff):
                    time.sleep(backoff[attempt])
                    continue
                reply_text = "Network error 🥲"
                break

        reply_text = clean_text(reply_text)
        reply_text = convert_amazon_links_to_affiliate(reply_text)

        messages = get_session_messages(session_id)
        messages.append({"role": "assistant", "content": reply_text})
        session_store[session_id] = trim_history(messages)

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"reply": f"Kachra crash rescued 😅: {e}"}), 200

# ------------------------------
# RESET
# ------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    sid = (request.get_json(force=True) or {}).get("session_id") or "anon"
    session_store.pop(sid, None)
    return jsonify({"message": "Chat reset!"}), 200

# ------------------------------
# RUN (LOCAL ONLY)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
