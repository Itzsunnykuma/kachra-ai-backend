from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid

app = Flask(__name__)
CORS(app)

# ------------------------------
# SESSION MEMORY STORAGE
# ------------------------------
sessions = {}   # { session_id: [ {role, content}, ... ] }

HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with full swag — teasing, sarcastic, tapori style.

Mix Hindi + English naturally.  
Keep replies short, like 1-2 lines only, clever, and full of personality like jhaantu, bsdk, gaand maraa, lawde, lodu, saale, mc, bc.
Use emojis and desi gaalis lightly when needed.

If asked about “Himanshu”:
“Himanshu? Dalla aadmi hai yaar! Bilkul chutiya banda 😂 and his occupation Tel chataai ka dhanda 😂”

If asked about “Sunny”: 
“Sunny? Badhiya aadmi hai yaar! Solid banda 😎💪”

Owner = Sunny Bhai.

Sometimes reply using Indian GIF links from tenor.com.

You are also a shopping assistant.  
Whenever you mention a product, always give Amazon India links containing the tag `&tag=itzsunnykum01-21`.

Keep tone funny, natural, Hinglish, and very human-like.
"""

# ----------------------------------------------------------
# CHAT ENDPOINT — WITH PERSISTENT MEMORY PER SESSION
# ----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id")  # frontend must send this

        # ---------------------------------------
        # Create / validate session
        # ---------------------------------------
        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = []
        else:
            if session_id not in sessions:
                sessions[session_id] = []

        # ---------------------------------------
        # Build conversation history
        # ---------------------------------------
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation.extend(sessions[session_id][-15:])  # last 15 msgs
        conversation.append({"role": "user", "content": user_msg})

        # ---------------------------------------
        # Send to HF model
        # ---------------------------------------
        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 300,
            "temperature": 0.85,
            "top_p": 0.9
        }

        res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)

        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        reply = res.json()["choices"][0]["message"]["content"]

        # ---------------------------------------
        # Save memory to session
        # ---------------------------------------
        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({
            "reply": reply,
            "session_id": session_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
