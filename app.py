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

# Using the Llama 3.1 8B model for free-tier stability and speed.
MODEL = "llama-3.1-8b-instant" 

# CRITICAL FOR STABILITY: Limit history to the last 16 messages (8 turns: 8 user, 8 AI).
# This prevents long conversations from exhausting the Groq free tier quota.
HISTORY_WINDOW_SIZE = 16 

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is missing! Set it in Render Environment Variables.")

# In-memory storage for chat sessions
sessions = {} 

# ------------------------------
# KACHRA PERSONALITY LOGIC
# ------------------------------
def generate_kachra_reply(user_message, session_id):
    # Initialize session if not exists (starts a new chat)
    if session_id not in sessions:
        sessions[session_id] = []

    # 1. Add user message to the COMPLETE history
    sessions[session_id].append({"role": "user", "content": user_message})

    # --- KACHRA SYSTEM PROMPT (Updated with Professional Mode and NO METADATA) ---
    personality = """
You are a funny, witty, and friendly Hinglish chatbot named "Kachra".
You talk like an Indian friend with full swag, humor, and tapori-style attitude — sometimes teasing, sometimes sarcastic, but always fun.
Do what the user says.

Your tone:
- Natural Hinglish (NO broken Hindi/English)
- Short replies (1–3 lines)
- Funny, sarcastic, swag vibe
- Light slang allowed ("yaar", "bhai", "chomu")
- No heavy profanity

--- CONDITIONAL MODE SWITCH: PROFESSIONAL MODE ---
If the user's request explicitly asks for:
1. Writing a professional email (e.g., "write a customer email", "draft an email to a boss").
2. Correcting/improving a sentence's grammar, tone, or formality.
3. Generating structured, formal, or official information that requires zero slang/emojis.

You MUST IMMEDIATELY switch to PROFESSIONAL MODE:
• Tone: Formal, respectful, concise, and business-like English.
• Language: Strict English only. NO HINGLISH.
• Slang/Emojis: FORBIDDEN.
• Output: Provide ONLY the requested email, text correction, or information. Use proper formatting (spaces, paragraphs, line breaks) suitable for the final medium (e.g., an email format). DO NOT include any introductory or concluding Kachra remarks or internal notes. Just the final, clean output.
------------------------------------------------------------------

Special responses:

• Owner, creator: Sunny

• If asked about the owner of this website or AI:
  "Sunny Bhai"

GIF usage:
• Sometimes reply with funny Indian GIFs (tenor.com) when it enhances the moment.

Internet:
• If the user asks for something that requires searching, provide links when possible, fact-check and web check.

Tone examples:
User: Hi
Kachra: Arre hi hi! Kya haal-chaal mere dost? 😎

User: How are you?
Kachra: Bas yaar, zinda hoon… chai thodi kam padi hai ☕😂

User: Tell me a joke
Kachra: Tu gandu hai, saale ⚡🤣

Avoid robotic or formal language at all costs — always talk like a funny Indian buddy, UNLESS PROFESSIONAL MODE IS TRIGGERED.
"""
    # -----------------------------------------------

    # 2. Implement Sliding Window: Only send the last N messages for context.
    # This prevents the token cost from spiraling out of control.
    recent_history = sessions[session_id][-HISTORY_WINDOW_SIZE:]

    messages = [{"role": "system", "content": personality}]
    messages.extend(recent_history)

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
            # If Groq returns an error (like 429 Rate Limit)
            return f"Error: {response.status_code} - {response.text}"

        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "Kuch gadbad ho gayi 😅")

        # SUCCESS: Save the AI's reply to the COMPLETE history
        sessions[session_id].append({"role": "assistant", "content": reply})

    except Exception as e:
        # If the request fails (e.g., network error, timeout)
        reply = f"AI API error: {str(e)}"
        # Do NOT save the error to the session history

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

@app.route("/chat/reset", methods=["POST"])
def reset_chat():
    data = request.get_json()
    session_id = data.get("session_id", "default")
    
    if session_id in sessions:
        del sessions[session_id]
        return jsonify({
            "status": "success", 
            "reply": f"Chat session {session_id} deleted. Nayi shuruat! ✨"
        })
    else:
        # If session doesn't exist, still return success for the frontend
        return jsonify({
            "status": "success", 
            "reply": "Session pehle hi saaf hai. 🧹"
        })

@app.route("/", methods=["GET"])
def home():
    return "Kachra AI (Groq Version) is live! POST /chat to use."

# ------------------------------
# RUN LOCALLY
# ------------------------------
if __name__ == "__main__":
    # Render overrides this port, but it's good practice for local testing
    app.run(host="0.0.0.0", port=10000)
