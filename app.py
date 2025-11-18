from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ------------------------------
# HF CONFIG
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# MEMORY (trimmed for stability)
# ------------------------------
session_memory = []
MAX_MEMORY = 10

SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
Talk like an Indian friend with full swag — teasing, sarcastic, tapori style.
Use short replies, Hinglish, emojis.

You are also a helpful AI shopping assistant,
but only give product links when the user asks.

Whenever you mention an Amazon India product,
append `&tag=itzsunnykum01-21`.
"""

ASSOCIATE_TAG = "itzsunnykum01-21"

# ------------------------------
# AMAZON AFFILIATE LINK MAKER
# ------------------------------
def convert_amazon_links_to_affiliate(text):
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace_link(match):
        url = match.group(0)
        if "tag=" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}tag={ASSOCIATE_TAG}"
        product_name = url.split("/")[-1].split("?")[0].replace("-", " ")
        return f'<a href="{url}" target="_blank" rel="noopener">{product_name}</a>'

    return re.sub(pattern, replace_link, text)

# ------------------------------
# SUPER STABLE HF REQUEST
# ------------------------------
def stable_hf_request(payload):
    MAX_RETRIES = 5
    RETRY_DELAY = 4

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                API_URL,
                headers=HEADERS,
                json=payload,
                timeout=150,
            )

            if response.status_code in [503, 504] or "loading" in response.text.lower():
                time.sleep(RETRY_DELAY + attempt * 2)
                continue

            return response

        except requests.exceptions.Timeout:
            time.sleep(RETRY_DELAY + attempt * 2)
            continue

        except Exception:
            time.sleep(RETRY_DELAY)
            continue

    return None


# ------------------------------
# HEALTH CHECK (REQUIRED FOR RENDER)
# ------------------------------
@app.route("/")
def home():
    return "OK", 200


# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")

        if not user_msg:
            return jsonify({"error": "Empty message"}), 400

        # Trim memory
        if len(session_memory) > MAX_MEMORY:
            session_memory[:] = session_memory[-MAX_MEMORY:]

        # Build full prompt
        full_prompt = SYSTEM_PROMPT + "\n\n"
        for msg in session_memory:
            full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
        full_prompt += f"USER: {user_msg}\nASSISTANT:"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.85,
                "top_p": 0.9,
                "return_full_text": False
            }
        }

        res = stable_hf_request(payload)

        if res is None:
            return jsonify({"error": "Model unreachable after retries"}), 500

        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        try:
            generated = res.json()[0]["generated_text"]
        except:
            generated = "Kachra on duty, but server crashed temporarily 😅 Try again!"

        reply = convert_amazon_links_to_affiliate(generated)

        # Save conversation
        session_memory.append({"role": "user", "content": user_msg})
        session_memory.append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# RESET ENDPOINT
# ------------------------------
@app.route("/reset", methods=["POST"])
def reset_chat():
    session_memory.clear()
    return jsonify({"message": "Chat reset successfully"}), 200


# ------------------------------
# RUN APP (RENDER-COMPATIBLE)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # REQUIRED for Render
    app.run(host="0.0.0.0", port=port)
