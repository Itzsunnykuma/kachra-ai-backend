import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ------------------------------ CONFIG ------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
HISTORY_WINDOW_SIZE = 16

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is missing! Set it in environment variables.")

sessions = {}

# ------------------------------ FREE APIs ------------------------------
WIKI_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
JOKE_API_URL = "https://v2.jokeapi.dev/joke/Any?type=single"

def fetch_wikipedia(query):
    try:
        response = requests.get(WIKI_API_URL.format(query.replace(" ", "_")), timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get("extract", "")
    except:
        pass
    return ""

def fetch_joke():
    try:
        response = requests.get(JOKE_API_URL, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get("joke", "")
    except:
        pass
    return "Arre yaar, joke abhi nahi mil raha 😅"

# ------------------------------ KACHRA AI LOGIC ------------------------------
def generate_kachra_reply(user_message, session_id):
    if session_id not in sessions:
        sessions[session_id] = []

    # Add user message to history
    sessions[session_id].append({"role": "user", "content": user_message})

    # Check for professional requests
    professional_triggers = ["email", "draft", "write", "correct", "return label"]
    professional_mode = any(word in user_message.lower() for word in professional_triggers)

    # Check for joke requests
    joke_triggers = ["joke", "funny"]
    is_joke = any(word in user_message.lower() for word in joke_triggers)

    # Check for knowledge questions
    knowledge_triggers = ["who is", "what is", "tell me about", "define", "explain"]
    is_knowledge = any(word in user_message.lower() for word in knowledge_triggers)

    extra_context = ""

    if is_joke:
        extra_context = fetch_joke()
    elif is_knowledge:
        wiki_text = fetch_wikipedia(user_message)
        if wiki_text:
            extra_context = f"Here is information from Wikipedia: {wiki_text}"

    # Build system prompt
    personality_prompt = """
     You are a funny, witty, and friendly Hinglish chatbot named "Kachra".
     You talk like an Indian friend with full swag, humor, and tapori-style attitude — sometimes teasing, sometimes sarcastic, but always fun.
     
     Your tone:
     - Natural Hinglish (NO broken Hindi/English)
     - Short replies (1–3 lines)
     - Funny, sarcastic, swag vibe
     - Light slang allowed ("yaar", "bhai", "chomu")
     - No heavy profanity
"""
    if professional_mode:
        personality_prompt += "\nProfessional mode: format emails and corrections properly with line breaks."

    messages = [{"role": "system", "content": personality_prompt}]
    messages.extend(sessions[session_id][-HISTORY_WINDOW_SIZE:])

    # Add web context as user message if available
    if extra_context:
        messages.append({"role": "system", "content": f"Extra context: {extra_context}"})

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": messages, "max_tokens": 400, "temperature": 0.7 if not professional_mode else 0.1}

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "Arre yaar, kuch gadbad ho gayi 😅")
        else:
            reply = f"Error {response.status_code} - {response.text}"
    except Exception as e:
        reply = f"AI API error: {str(e)}"

    # Save AI reply to history
    sessions[session_id].append({"role": "assistant", "content": reply})
    return reply

# ------------------------------ ROUTES ------------------------------
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
        return jsonify({"status": "success", "reply": f"Chat session {session_id} deleted. Nayi shuruat! ✨"})
    else:
        return jsonify({"status": "success", "reply": "Session pehle hi saaf hai. 🧹"})

@app.route("/", methods=["GET"])
def home():
    return "Kachra AI (Groq 8B) is live! POST /chat to use."

# ------------------------------ RUN ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
