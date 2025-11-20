import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ------------------------------
# CONFIG (GROQ VERSION)
# ------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is missing! Set it in Render Environment Variables.")

sessions = {}

# ------------------------------
# KACHRA PERSONALITY
# ------------------------------
def generate_kachra_reply(user_message, session_id):
    if session_id not in sessions:
        sessions[session_id] = []

    sessions[session_id].append({"role": "user", "content": user_message})

    personality = (
        "You are Kachra 😎 — a funny, witty Hinglish chatbot. "
        "Reply in short, funny Hinglish sentences with emojis. "
        "Never speak long paragraphs. "
        "If anyone mentions Sunny, reply only: 'Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪'. "
        "Stay in character ALWAYS."
    )

    messages = [{"role": "system", "content": personality}]
    messages.extend(sessions[session_id])

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 200,
        "temperature": 0.9
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "Kuch gadbad ho gayi 😅")

    except Exception as e:
        reply = f"AI API error: {str(e)}"

    sessions[session_id].append({"role": "assistant", "content": reply})
    return reply

# ------------------------------
# ROUTES
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"reply": "Message missing!", "session_id": session_id})

    reply = generate_kachra_reply(message, session_id)
    return jsonify({"reply": reply, "session_id": session_id})

@app.route("/", methods=["GET"])
def home():
    return "Kachra AI (Groq Version) is live! POST /chat to use."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
