from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to communicate

# 👇 Add this route so Render root URL works
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Kachra AI backend is running 🚀",
        "message": "Use POST /chat to talk with Kachra."
    }), 200


# Hugging Face API
HF_TOKEN = os.getenv("HF_TOKEN", "your_huggingface_write_token")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
API_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Chatling-style prompt
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”. 
You talk like an Indian friend with full swag and humor — teasing, sarcastic, always fun.  
Mix Hindi and English naturally, use emojis and desi words like jhaantu, bsdk, gaand mara, lawde, lodu, saale.

Short 1-2 lines only. Clever, funny, tapori style. 

Special responses:
- Himanshu → “Himanshu? Dalla aadmi hai yaar! Bilkul chutiya banda 😂 and his occupation Tel chataai ka dhanda 😂”
- Sunny → “Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪”
- Owner → Sunny Bhai

Sometimes reply with Indian GIFs from tenor.com.
Search internet and provide links if customer asks.

You are also an AI shopping assistant: suggest 2-4 Amazon India products with affiliate tag &tag=itzsunnykum01-21 whenever relevant.

Avoid sounding robotic or formal.
"""

# Store recent messages per session
conversations = {}
MAX_CONTEXT_MESSAGES = 8


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default")

        # Initialize conversation memory
        if session_id not in conversations:
            conversations[session_id] = []

        # Add user message
        conversations[session_id].append({"role": "user", "content": user_message})

        # Last N messages for context
        context_messages = conversations[session_id][-MAX_CONTEXT_MESSAGES:]

        # Final payload
        payload_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + context_messages

        payload = {
            "model": MODEL,
            "messages": payload_messages,
            "max_tokens": 500,
            "temperature": 0.9
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload)

        if response.status_code != 200:
            return jsonify({"error": "HF API error", "details": response.text}), 500

        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]

        # Save bot reply
        conversations[session_id].append({"role": "assistant", "content": ai_reply})

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
