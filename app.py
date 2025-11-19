from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
from bs4 import BeautifulSoup
import random

app = Flask(__name__)
CORS(app)

# ------------------------------
# Hugging Face Config
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Llama-2-8b-chat-hf"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# In-memory conversation store
# ------------------------------
conversations = {}

# ------------------------------
# Kachra Personality Prompt
# ------------------------------
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”. 
You talk like an Indian friend with full swag and humor — teasing, sarcastic, but always fun.  
Mix Hindi and English naturally in every sentence. Use emojis and desi expressions like tapori.

Keep replies short (1-2 lines), clever, and full of personality like jhaantu, dalle, gand maraa, lawde, lodu, saale.

If anyone mentions “Sunny” or asks about him, reply: 
“Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪”

Always chat like a funny Indian buddy.  
Help users find the best and most relevant products from Amazon India with affiliate tag &tag=itzsunnykum01-21.
If you don't know something, search the internet and provide a relevant link.
"""

MAX_HISTORY_CHARS = 4000
AMAZON_KEYWORDS = ["suggest", "recommend", "product", "buy", "phone", "laptop", "clothes", "gadgets", "beauty", "kitchen"]

EMOJIS = ["😎","😂","💪","⚡","🔥","💥","🤣","☕","😉"]
SLANG = ["jhaantu","saale","lawde","lodu","gand maraa","dalle","tapori","chikna"]

# ------------------------------
# Emoji & Tapori swag injection
# ------------------------------
def inject_swag(text):
    if not any(e in text for e in EMOJIS):
        text += " " + random.choice(EMOJIS)
    if len(text.split()) < 15 and random.random() > 0.5:
        text += f" {random.choice(SLANG)}"
    return text

# ------------------------------
# Amazon search
# ------------------------------
def search_amazon(product_name):
    try:
        query = "+".join(product_name.strip().split())
        url = f"https://www.amazon.in/s?k={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for a in soup.select("a.a-link-normal.s-no-outline")[:5]:
            title = a.get_text().strip()
            href = "https://www.amazon.in" + a.get("href") + "&tag=itzsunnykum01-21"
            parent = a.find_parent("div", {"data-component-type": "s-search-result"})
            rating_tag = parent.select_one("span.a-icon-alt") if parent else None
            rating = rating_tag.get_text().split()[0] if rating_tag else ""
            results.append(f"[{title}]({href}){' ⭐'+rating if rating else ''}")
        return results if results else ["No results found 😅"]
    except Exception:
        return ["Cannot fetch Amazon results right now 😅"]

# ------------------------------
# Web search fallback
# ------------------------------
def search_web(query):
    try:
        search_url = f"https://www.google.com/search?q={'+'.join(query.split())}"
        return [f"[Click here to search on Google]({search_url})"]
    except Exception:
        return ["Cannot fetch search results 😅"]

# ------------------------------
# Chat Endpoint
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id") or str(uuid.uuid4())

        if not user_message:
            return jsonify({"reply": "Arre yaar, kuch type karo 😅", "session_id": session_id})

        if session_id not in conversations:
            conversations[session_id] = []

        conversations[session_id].append({"role": "user", "content": user_message})

        # ------------------------------
        # Automatic Amazon search
        # ------------------------------
        amazon_response = ""
        web_response = ""
        if any(word in user_message.lower() for word in AMAZON_KEYWORDS):
            links = search_amazon(user_message)
            amazon_response = "Here are some great options 👇\n" + "\n".join(f"• {link}" for link in links)
        else:
            # fallback web search for non-Amazon queries
            links = search_web(user_message)
            web_response = "Check this out 👇\n" + "\n".join(f"• {link}" for link in links)

        # ------------------------------
        # Build AI prompt with truncation
        # ------------------------------
        history_text = ""
        for msg in reversed(conversations[session_id]):
            role = "User" if msg["role"] == "user" else "AI"
            history_text = f"{role}: {msg['content']}\n" + history_text
            if len(history_text) > MAX_HISTORY_CHARS:
                break

        prompt = SYSTEM_PROMPT + "\n\n" + history_text + "AI:"

        payload = {"inputs": prompt, "options": {"wait_for_model": True}}
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            return jsonify({"reply": f"AI API error: {response.text}", "session_id": session_id})

        ai_output = response.json()
        ai_reply = ai_output[0]["generated_text"] if ai_output else "Kya baat hai, reply nahi mila 😅"

        # Append Amazon or web links
        if amazon_response:
            ai_reply += "\n\n" + amazon_response
        elif web_response:
            ai_reply += "\n\n" + web_response

        # Inject tapori swag & emojis
        ai_reply = inject_swag(ai_reply)

        conversations[session_id].append({"role": "ai", "content": ai_reply})

        return jsonify({"reply": ai_reply, "session_id": session_id})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed 😅: {str(e)}", "session_id": session_id})

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
