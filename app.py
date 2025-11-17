from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
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
# SINGLE SESSION MEMORY
# ------------------------------
session_memory = []  # Stores full conversation (user + assistant)

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with full swag — teasing, sarcastic, tapori style.

Mix Hindi + English naturally.  
Keep replies short, like 1-2 lines only, clever, and full of personality.
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
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace_link(match):
        url = match.group(0)
        if "tag=" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}tag={ASSOCIATE_TAG}"

        # Extract product name
        segments = url.split("/")
        product_name = segments[-2] if len(segments) > 2 else segments[-1]
        product_name = re.sub(r"[-_]", " ", product_name)
        product_name = re.sub(r"\?.*$", "", product_name)
        product_name = product_name[:50] + "..." if len(product_name) > 50 else product_name
        return f'<a href="{url}" target="_blank" rel="noopener">{product_name}</a>'

    return re.sub(pattern, replace_link, text)

# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "")

        # Initialize session with system prompt if empty
        if not session_memory:
            session_memory.append({"role": "system", "content": SYSTEM_PROMPT})

        # Append user message
        session_memory.append({"role": "user", "content": message})

        # Prepare payload for HF with full conversation
        payload = {
            "model": MODEL,
            "messages": session_memory,
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

        # Append assistant reply
        session_memory.append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------
# RESET CHAT ENDPOINT
# ------------------------------
@app.route("/reset", methods=["POST"])
def reset_chat():
    global session_memory
    session_memory = []  # Clear full memory
    return jsonify({"message": "Chat memory cleared! Start fresh with Kachra 😎"}), 200

# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
