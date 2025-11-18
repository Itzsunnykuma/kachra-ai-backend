from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import time

app = Flask(__name__)
CORS(app)

# ---------------------------------
# Hugging Face Config
# ---------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"   # fastest + smallest

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ---------------------------------
# Stable Memory
# ---------------------------------
MAX_HISTORY = 8              # More stable than 6
session_memory = []

# ---------------------------------
# System Prompt
# ---------------------------------
SYSTEM_PROMPT = """
You are a funny Hinglish chatbot named Kachra 😂.
Talk like an Indian friend – short, witty, savage replies (1–2 lines max).
Owner = Sunny.
"""

ASSOCIATE_TAG = "itzsunnykum01-21"

# ---------------------------------
# Amazon Link Converter
# ---------------------------------
def convert_amazon_links_to_affiliate(text):
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace(match):
        url = match.group(0)
        if "tag=" not in url:
            url += ("&" if "?" in url else "?") + f"tag={ASSOCIATE_TAG}"
        name = url.split("/")[-2].replace("-", " ")
        name = re.sub(r"\?.*$", "", name)
        name = (name[:50] + "...") if len(name) > 50 else name
        return f'<a href="{url}" target="_blank">{name}</a>'

    return re.sub(pattern, replace, text)

# ---------------------------------
# Clean malformed responses
# ---------------------------------
def clean_text(text):
    if not isinstance(text, str):
        return "Oops, something went glitchy 😅"
    return text.replace("\u0000", "").strip()

# ---------------------------------
# Chat Endpoint
# ---------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")

        if not HF_TOKEN:
            return jsonify({"reply": "Missing HF_TOKEN 🙄"}), 500

        # Initialize memory with system prompt
        if not session_memory:
            session_memory.append({"role": "system", "content": SYSTEM_PROMPT})

        # Add user message
        session_memory.append({"role": "user", "content": user_msg})

        # Trim conversation (stability upgrade)
        conversation = session_memory[-MAX_HISTORY:]

        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 250,
            "temperature": 0.75,     # more stable
            "top_p": 0.9
        }

        # ---------------------------
        # Retry Logic + Failover Mode
        # ---------------------------
        reply = None
        for attempt in range(3):
            try:
                r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=40)

                if r.status_code == 200:
                    reply = r.json()["choices"][0]["message"]["content"]
                    break

                # If overloaded → fallback to safer mode
                payload["temperature"] = 0.3
                payload["top_p"] = 0.7

            except Exception:
                time.sleep(1.5)

        if not reply:
            reply = "Arre router ka mood kharab hai 😭 thoda der baad try karo."

        reply = clean_text(reply)
        reply = convert_amazon_links_to_affiliate(reply)

        session_memory.append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Crash prevented: {str(e)}"}), 200

# ---------------------------------
# Reset
# ---------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    global session_memory
    session_memory = []
    return jsonify({"message": "Chat reset! Kachra ready 😎"}), 200

# ---------------------------------
# Run
# ---------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
