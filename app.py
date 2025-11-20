import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ------------------------------
# CONFIG (UPDATED FOR GROQ)
# ------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq uses an OpenAI-compatible URL
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Llama 3 on Groq
MODEL = "llama3-8b-8192"

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is missing! Set it in Render Environment Variables.")

# In-memory sessions
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

    # Groq expects the system prompt to be part of the messages list logic
    # We prepend it here conceptually, or send it as the first message
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
        # We use the generic requests library so you don't need to change requirements.txt
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            return f"Error from Groq: {response.status_code} - {response.text}"

        data = response.json()

        reply = (
            data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "Kuch gadbad ho gayi 😅")
        )

    except Exception as e:
        reply = f"AI API error: {str(e)}"

    # Save AI reply
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


# ------------------------------
# RUN LOCALLY
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
