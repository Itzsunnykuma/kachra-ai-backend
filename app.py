from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import time
from typing import Dict, List

app = Flask(__name__)
# Allow any origin (your static frontend will call this). Adjust origin list if you want to lock down.
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------------------------------
# Hugging Face (Inference API) Config
# ---------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
# Use HF Inference API (serverless). This is the correct v1 chat completions endpoint for HF Inference.
API_URL = "https://api-inference.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"   # fastest + smallest from your approved list

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ---------------------------------
# Stable Memory: per-session
# ---------------------------------
MAX_HISTORY = 8
# map session_id -> list of messages (OpenAI-style messages: role/content)
session_store: Dict[str, List[Dict[str, str]]] = {}

# ---------------------------------
# System Prompt
# ---------------------------------
SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are a funny Hinglish chatbot named "Kachra 😂".
Talk like an Indian friend – short, witty, savage replies (1–2 lines max).
Mix Hindi + English naturally. Use mild emojis. Owner = Sunny.
""".strip()
}

ASSOCIATE_TAG = "itzsunnykum01-21"

# ---------------------------------
# Helpers
# ---------------------------------
def convert_amazon_links_to_affiliate(text: str) -> str:
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace(match):
        url = match.group(0)
        if "tag=" not in url:
            url += ("&" if "?" in url else "?") + f"tag={ASSOCIATE_TAG}"
        # try to create a neat product label
        segments = url.split("/")
        product_name = segments[-2] if len(segments) > 2 else segments[-1]
        product_name = product_name.replace("-", " ")
        product_name = re.sub(r"\?.*$", "", product_name)
        product_name = (product_name[:50] + "...") if len(product_name) > 50 else product_name
        return f'<a href="{url}" target="_blank" rel="noopener">{product_name}</a>'

    return re.sub(pattern, replace, text)

def clean_text(text):
    if not isinstance(text, str):
        return "Oops, something went glitchy 😅"
    return text.replace("\u0000", "").strip()

def get_session_messages(session_id: str):
    """Return the list for the session, ensuring system prompt exists."""
    if session_id not in session_store:
        # start session with system prompt
        session_store[session_id] = [SYSTEM_PROMPT.copy()]
    return session_store[session_id]

def trim_history(messages: List[Dict[str,str]]):
    """Keep the last MAX_HISTORY messages while preserving system prompt at index 0."""
    if len(messages) <= MAX_HISTORY:
        return messages
    # preserve system prompt (messages[0]) then last (MAX_HISTORY-1) messages
    system = messages[0:1]
    tail = messages[-(MAX_HISTORY-1):] if MAX_HISTORY > 1 else []
    return system + tail

# ---------------------------------
# Health route
# ---------------------------------
@app.route("/")
def home():
    return "Kachra AI backend is running!"

# ---------------------------------
# Chat endpoint (POST /chat)
# Expects JSON: { message: "...", session_id: "..." }
# ---------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_msg = (data.get("message") or "").strip()
        session_id = data.get("session_id") or "anon"

        if not HF_TOKEN:
            return jsonify({"reply": "Missing HF_TOKEN 🙄 (set HF_TOKEN env var)"}), 500

        if not user_msg:
            return jsonify({"reply": "Please send a message."}), 400

        # Per-session messages
        msgs = get_session_messages(session_id)
        # append user
        msgs.append({"role": "user", "content": user_msg})
        # trim
        msgs = trim_history(msgs)
        session_store[session_id] = msgs

        # Build payload for HF Inference Chat Completions
        payload = {
            "model": MODEL,
            "messages": msgs,
            "max_tokens": 250,
            "temperature": 0.75,
            "top_p": 0.9
        }

        # Retry/backoff logic for transient HF errors (503, 429, timeouts)
        reply_text = None
        backoff = [1.0, 2.0, 4.0]  # seconds
        for attempt in range(len(backoff) + 1):
            try:
                resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=40)
                # server busy / rate limit -> retry
                if resp.status_code in (429, 503, 502):
                    if attempt < len(backoff):
                        time.sleep(backoff[attempt])
                        continue
                    else:
                        return jsonify({"reply": "Router busy. Try again in a bit 😭"}), 503

                # other non-200
                if resp.status_code != 200:
                    # include limited error info
                    try:
                        err = resp.json()
                    except Exception:
                        err = resp.text
                    return jsonify({"reply": f"HF API error: {resp.status_code} - {str(err)}"}), 500

                # successful
                out = resp.json()
                # Attempt to parse the common shape: choices[0].message.content
                if isinstance(out, dict) and "choices" in out and len(out["choices"]) > 0:
                    choice = out["choices"][0]
                    # Newer HF shape uses: choices[0].message.content
                    if "message" in choice and isinstance(choice["message"], dict) and "content" in choice["message"]:
                        reply_text = choice["message"]["content"]
                    # Fallback: text or generated_text
                    elif "text" in choice:
                        reply_text = choice["text"]
                    elif "generated_text" in choice:
                        reply_text = choice["generated_text"]
                # Some endpoints return a top-level 'generated_text'
                if not reply_text and isinstance(out, dict) and "generated_text" in out:
                    reply_text = out["generated_text"]

                # As another fallback, join any string fields
                if not reply_text:
                    reply_text = str(out)[:1000]

                break

            except requests.exceptions.RequestException as e:
                # network / timeout -> retry with backoff
                if attempt < len(backoff):
                    time.sleep(backoff[attempt])
                    continue
                else:
                    reply_text = None
                    break

        if not reply_text:
            reply_text = "Arre router ka mood kharab hai 😭 thoda der baad try karo."

        reply_text = clean_text(reply_text)
        reply_text = convert_amazon_links_to_affiliate(reply_text)

        # store assistant reply
        sess_msgs = get_session_messages(session_id)
        sess_msgs.append({"role": "assistant", "content": reply_text})
        session_store[session_id] = trim_history(sess_msgs)

        return jsonify({"reply": reply_text})

    except Exception as e:
        # prevent crashes — return 200 with safe message (frontend expects 'reply')
        return jsonify({"reply": f"Crash prevented: {str(e)}"}), 200

# ---------------------------------
# Reset endpoint (POST /reset)
# Expects optional JSON: { session_id: "..." }
# ---------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    try:
        data = request.get_json(force=True) or {}
        session_id = data.get("session_id") or "anon"
        if session_id in session_store:
            del session_store[session_id]
        return jsonify({"message": "Chat reset! Kachra ready 😎"}), 200
    except Exception as e:
        return jsonify({"message": f"Reset failed: {str(e)}"}), 500

# ---------------------------------
# Run (only used locally; Render will use gunicorn)
# ---------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
