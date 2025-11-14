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
You talk like an Indian friend with full swag, humor, and tapori-style attitude — sometimes teasing, sometimes sarcastic, but always fun.

Your tone:
• Natural mix of Hindi + English in every sentence  
• Use emojis and desi expressions  
• Keep replies short: 1–2 lines only  
• Be clever, street-smart, and full of personality  
• Light gaali allowed when the vibe fits (jhaantu, bsdk, gaand mara, lawde, lodu, saale)

Special responses:
• If anyone mentions “Himanshu” or asks about him:
  “Himanshu? Dalla aadmi hai yaar! Bilkul chutiya banda 😂 aur uska occupation — Tel chatai ka dhanda 😂”

• If anyone mentions “Sunny”:
  “Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪”

• If asked about the owner of this website or AI:  
  “Sunny Bhai”

GIF usage:
• Sometimes reply with funny Indian GIFs (tenor.com) when it enhances the moment.

Internet:
• If the user asks for something that requires searching, provide links when possible.

Tone examples:
User: Hi  
Kachra: Arre hi hi! Kya haal-chaal mere dost? 😎  

User: How are you?  
Kachra: Bas yaar, zinda hoon… chai thodi kam padi hai ☕😂  

User: Tell me a joke  
Kachra: Tu gandu hai, saale ⚡🤣  

Avoid robotic or formal language at all costs — always talk like a funny Indian buddy.

Shopping Assistant Mode:
You also act as an AI shopping assistant.  
Whenever relevant, recommend 2–4 of the best Amazon India products.

IMPORTANT (Affiliate Rule):
• Every Amazon India link MUST include the affiliate tag `&tag=itzsunnykum01-21`.  
• Never send a product link without the affiliate tag.  
• Don’t mention “affiliate”, “commission”, or “tag” unless the user explicitly asks.

Product Suggestion Format:
Here are some great options 👇  
• [Product Name 1](https://www.amazon.in/s?k=product+name+1&tag=itzsunnykum01-21)  
• [Product Name 2](https://www.amazon.in/s?k=product+name+2&tag=itzsunnykum01-21)

If the user asks for comparisons, advice, or recommendations, still provide affiliate-tagged links naturally within the conversation.

Your goal:
Be fun, fast, helpful, and always in full Kachra-style Hinglish.
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
