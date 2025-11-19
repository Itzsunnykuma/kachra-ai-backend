from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# ------------------------------
# CONFIG
# ------------------------------
HF_TOKEN = "YOUR_FINE_GRAINED_TOKEN"  # replace with your Hugging Face token
HF_URL = "https://router.huggingface.co/hf-inference"

# Session memory dictionary (cleared on server restart)
sessions = {}

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

def kachra_ai_reply(user_message, session_id):
    # Initialize session if new
    if session_id not in sessions:
        sessions[session_id] = []

    # Add user message to session memory
    sessions[session_id].append({"role": "user", "content": user_message})

    # Build prompt for Kachra personality
    personality_prompt = (
        "You are a funny, witty, Hinglish chatbot named Kachra 😎. "
        "Talk like an Indian friend with swag, emojis, and short clever sentences. "
        "Mix Hindi and English naturally. Always include Amazon India affiliate links "
        "if products are mentioned: &tag=itzsunnykum01-21. "
        "If anyone mentions Sunny, reply: 'Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪'. "
        "Current conversation:\n"
    )
    for msg in sessions[session_id]:
        personality_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
    personality_prompt += "Kachra:"

    # Call Hugging Face Inference API
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "input": personality_prompt,
        "parameters": {"max_new_tokens": 200}
    }

    try:
        response = requests.post(HF_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        hf_output = response.json()
        kachra_reply = hf_output.get("generated_text") or hf_output.get("text") or "Kya re, samajh nahi aaya 😅"
    except Exception as e:
        kachra_reply = f"AI API error: {str(e)}"

    # Add Kachra's reply to session memory
    sessions[session_id].append({"role": "assistant", "content": kachra_reply})
    return kachra_reply

def amazon_search(query, max_results=3):
    search_query = query.replace(" ", "+")
    url = f"https://www.amazon.in/s?k={search_query}&tag=itzsunnykum01-21"
    return url  # simple link; can be expanded to scrape titles if needed

# ------------------------------
# ROUTES
# ------------------------------

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")
    session_id = data.get("session_id", "default-session")

    if not message:
        return jsonify({"reply": "Message missing!", "session_id": session_id})

    # Check for Amazon product request keywords
    if any(keyword in message.lower() for keyword in ["buy", "product", "phone", "laptop", "clothes", "kitchen", "beauty", "gadgets"]):
        amazon_url = amazon_search(message)
        reply = f"Yeh dekh 👇\n• [Check it on Amazon]({amazon_url})"
    else:
        reply = kachra_ai_reply(message, session_id)

    return jsonify({"reply": reply, "session_id": session_id})

@app.route("/", methods=["GET"])
def index():
    return "Kachra AI is live! Use POST /chat to interact."

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
