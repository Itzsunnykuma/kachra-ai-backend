from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import time

app = Flask(__name__)
CORS(app)

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# MEMORY (with stability trimming)
# ------------------------------
session_memory = []
MAX_MEMORY = 10  # prevents runaway memory (stability, not logic change)

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
# VERY STABLE REQUEST FUNCTION
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
                timeout=150,          # Highest stable timeout
            )

            # HuggingFace warm-up status
            if response.status_code in [503, 504] or "loading" in response.text.lower():
                time.sleep(RETRY_DELAY + attempt * 2)  # exponential backoff
                continue

            return response

        except requests.exceptions.Timeout:
            time.sleep(RETRY_DELAY + attempt * 2)
            continue

        except Exception:
            time.sleep(RETRY_DELAY)
            continue

    return None  # total failure fallback


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

        # Trim memory for stability (without changing behavior)
        if len(session_memory) > MAX_MEMORY:
            session_memory[:] = session_memory[-MAX_MEMORY:]

        # Build prompt
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

        # Ultra-stable call
        res = stable_hf_request(payload)

        if res is None:
            return jsonify({"error": "Model unreachable after retries"}), 500

        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        # Clean generated text safely
        try:
            generated = res.json()[0]["generated_text"]
        except:
            generated = "Kachra on duty, but server crashed temporarily 😅 Try again!"

        reply = convert_amazon_links_to_affiliate(generated)

        # Store memory
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
