from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import re

app = Flask(__name__)
CORS(app)

# ------------------------------
# HF MODEL CONFIG
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# SESSION MEMORY
# ------------------------------
sessions = {}  # {session_id: [ {role, content}, ... ]}

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with full swag — teasing, sarcastic, tapori style.

Mix Hindi + English naturally.  
Keep replies short, like 1-2 lines only, clever, and full of personality like jhaantu, bsdk, gaand maraa, lawde, lodu, saale, mc, bc.
Use emojis and desi gaalis lightly when needed.

Owner = Sunny Bhai.

Sometimes reply using Indian GIF links from tenor.com.

You are also a shopping assistant.  
Whenever you mention a product, always give Amazon India links containing the tag `&tag=itzsunnykum01-21`.
"""

ASSOCIATE_TAG = "itzsunnykum01-21"

# ------------------------------
# HELPER: CONVERT AMAZON LINKS TO AFFILIATE
# ------------------------------
def convert_amazon_links_to_affiliate(text):
    """
    Find all Amazon links and add affiliate tag automatically.
    """
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace_link(match):
        url = match.group(0)
        if "tag=" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}tag={ASSOCIATE_TAG}"

        # Try to extract product name from URL path
        segments = url.split("/")
        product_name = segments[-2] if len(segments) > 2 else segments[-1]
        product_name = re.sub(r"[-_]", " ", product_name)
        product_name = re.sub(r"\?.*$", "", product_name)
        product_name = product_name[:50] + "..." if len(product_name) > 50 else product_name
        return f'<a href="{url}" target="_blank" rel="noopener">{product_name}</a>'

    return re.sub(pattern, replace_link, text)

# ------------------------------
# HELPER: GET OR CREATE SESSION
# ------------------------------
def get_session(session_id=None):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = []
    return session_id, sessions[session_id]

# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "")
        session_id = data.get("session_id")

        session_id, session_memory = get_session(session_id)

        # Keep last 8 exchanges to limit prompt size
        MAX_MEMORY = 8
        session_memory = session_memory[-MAX_MEMORY:]

        # Ensure system prompt first
        if not any(m['role'] == 'system' for m in session_memory):
            session_memory.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

        # Prepare messages for HF
        payload = {
            "model": MODEL,
            "messages": session_memory + [{"role": "user", "content": message}],
            "max_tokens": 300,
            "temperature": 0.85,
            "top_p": 0.9
        }

        res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        reply = res.json()["choices"][0]["message"]["content"]

        # Convert Amazon links
        reply = convert_amazon_links_to_affiliate(reply)

        # Save assistant reply in session memory
        session_memory.append({"role": "user", "content": message})
        session_memory.append({"role": "assistant", "content": reply})
        sessions[session_id] = session_memory[-MAX_MEMORY:]

        return jsonify({"session_id": session_id, "reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
