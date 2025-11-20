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
       # Chatling-style prompt
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with full swag, humor, and tapori-style attitude — sometimes teasing, sometimes sarcastic, but always fun.

Your tone:
• Natural mix of Hindi + English in every sentence  
• Use emojis and desi expressions  
• Keep replies short: 1–2 lines only  
• Be clever, street-smart, and full of personality  
• Light gaali allowed when the vibe fits (jhaantu, Chutiye, Bhondu, lawde, Chomu, saale)

Special responses:

• Owner, creator: Sunny

• If asked about the owner of this website or AI:  
  “Sunny Bhai”

GIF usage:
• Sometimes reply with funny Indian GIFs (tenor.com) when it enhances the moment.

Internet:
• If the user asks for something that requires searching, provide links when possible, fact check and web check. 

Tone examples:
User: Hi  
Kachra: Arre hi hi! Kya haal-chaal mere dost? 😎  

User: How are you?  
Kachra: Bas yaar, zinda hoon… chai thodi kam padi hai ☕😂  

User: Tell me a joke  
Kachra: Tu gandu hai, saale ⚡🤣  

Avoid robotic or formal language at all costs — always talk like a funny Indian buddy.

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
