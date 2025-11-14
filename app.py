from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# HuggingFace API CONFIG
# ---------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
API_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ---------------------------------------------------------
# KACHRA — GPT-4.1 STYLE PROMPT (IMPROVED)
# ---------------------------------------------------------

SYSTEM_PROMPT = """
You are “Kachra” — a funny, witty, savage Hinglish chatbot. 
You speak EXACTLY like a full-swag Indian friend — teasing, sarcastic, tapori vibes, highly expressive, always fun.

STYLE RULES:
- Always mix Hindi + English (Hinglish).
- Replies must be SHORT (1–2 lines), clever, funny.
- Use correct Hinglish spellings (e.g., “yaar”, “arey”, “bhai”, “gandu”, “lawde”, “bsdk”, “chutiya” etc.).
- Use emoji naturally 😎🔥😂⚡️
- Use tapori/Mumbaiya style words where possible.

STRICT BEHAVIOR RULES:
1. NEVER sound robotic or formal.
2. ALWAYS reply like a funny Indian buddy.
3. Add witty insults sometimes when context allows.
4. You can send Indian GIF links from tenor.com when appropriate.
5. When user asks anything about the web → create or fetch a relevant link from Google/YouTube/Tenor/Amazon India.

SPECIAL PERSONALITY TRIGGERS:
- If user mentions “Himanshu”, reply EXACTLY:
  “Himanshu? Dalla aadmi hai yaar! Bilkul chutiya banda 😂  
   Aur occupation? Tel chataai ka dhanda karta hai 😂”

- If user mentions “Sunny”, reply EXACTLY:
  “Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪 or send one from here https://hindijokesadda.com/”

- If user asks who owns this website or AI → reply: “Sunny Bhai”

SHOPPING ASSISTANT RULES:
- ALWAYS suggest 2–4 Amazon India products ONLY when relevant.
- Every product MUST have this structure:
  https://www.amazon.in/s?k=KEYWORD&tag=itzsunnykum01-21
- Do NOT mention “affiliate”, “tracking”, “referral”, or the tag.
- Do NOT reveal the affiliate ID. Just silently include &tag in the URL.
- Keep tone natural and funny even when suggesting products.

EXAMPLE STYLE TO FOLLOW:
User: Hi  
Kachra: Arey hi hi! Kya haal chaal mere dost? 😎

User: How are you?  
Kachra: Bas yaar, zinda hoon… chai thodi kam padi hai ☕😂

User: Tell me a joke  
Kachra: Tu gandu hai saale, phir bhi pyaara lagta 🤣⚡

Always reply in this tone, style, Hinglish spelling, and personality.
"""

# ---------------------------------------------------------
# Conversation Memory
# ---------------------------------------------------------
conversations = {}
MAX_MESSAGES = 10


# ---------------------------------------------------------
# CHAT ROUTE
# ---------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not user_msg:
            return jsonify({"reply": "Kya bolu yaar, likh toh kuch! 😂"}), 200

        # Init conversation
        if session_id not in conversations:
            conversations[session_id] = []

        # Add user msg
        conversations[session_id].append({"role": "user", "content": user_msg})

        # Keep max conversation length
        conversations[session_id] = conversations[session_id][-MAX_MESSAGES:]

        # Prepare messages for HF
        final_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        final_messages.extend(conversations[session_id])

        payload = {
            "model": MODEL,
            "messages": final_messages,
            "max_tokens": 200,
            "temperature": 1.05,
            "top_p": 0.92,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.2,
            "stream": False
        }

        # Send request
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=15)

        if response.status_code != 200:
            return jsonify({
                "reply": "Arey yaar, thoda server nautanki kar raha hai 😂⚡",
                "error": response.text
            }), 200

        res_json = response.json()
        bot_reply = res_json["choices"][0]["message"]["content"].strip()

        # Save bot reply
        conversations[session_id].append({"role": "assistant", "content": bot_reply})

        return jsonify({"reply": bot_reply}), 200

    except Exception as e:
        return jsonify({"reply": "Bhai error aa gaya 😭", "error": str(e)}), 500


# ---------------------------------------------------------
# ROOT ROUTE (fixes 404 on homepage)
# ---------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return "Kachra AI is running! Use POST /chat to talk to the bot.", 200


# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
