from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# ------------------------------
# Hugging Face Router API Config
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Llama-2-8b-chat-hf"
API_URL = f"https://router.huggingface.co/api/models/{MODEL}"  # Correct endpoint
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# Session memory (lost on refresh)
# ------------------------------
conversations = {}

# ------------------------------
# Kachra personality
# ------------------------------
SYSTEM_PROMPT = """
You are Kachra, a funny, witty, Hinglish chatbot with swag 😎.
Use emojis and desi expressions (tapori slang like jhaantu, lawde, saale).
Keep replies short, clever, and 1–2 lines max.
Mention Sunny Bhai when asked about the owner.
Provide Amazon India product links with affiliate tag &tag=itzsunnykum01-21.
Fallback to Google search links if Amazon results aren’t found.
"""

AMAZON_KEYWORDS = ["suggest", "recommend", "buy", "product", "phone", "laptop", "clothes", "gadgets", "beauty", "kitchen"]

# ------------------------------
# Helper functions
# ------------------------------
def amazon_search(query):
    try:
        q = "+".join(query.strip().split())
        url = f"https://www.amazon.in/s?k={q}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        items = []
        for a in soup.select("a.a-link-normal.s-no-outline")[:4]:
            title = a.get_text().strip()
            href = "https://www.amazon.in" + a.get("href") + "&tag=itzsunnykum01-21"
            items.append(f"[{title}]({href})")
        return items if items else ["No results found 😅"]
    except Exception:
        return ["Cannot fetch Amazon results 😅"]

def web_search(query):
    url = f"https://www.google.com/search?q={'+'.join(query.split())}"
    return [f"[Click here to search]({url})"]

# ------------------------------
# Chat endpoint
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id") or str(uuid.uuid4())

    if not user_message:
        return jsonify({"reply": "Arre yaar, kuch type karo 😅", "session_id": session_id})

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": user_message})

    # Amazon search trigger
    amazon_results = []
    if any(word in user_message.lower() for word in AMAZON_KEYWORDS):
        amazon_results = amazon_search(user_message)

    # Build prompt with conversation history
    history_text = ""
    for msg in conversations[session_id][-10:]:  # last 10 messages
        role = "User" if msg["role"] == "user" else "AI"
        history_text += f"{role}: {msg['content']}\n"
    prompt = SYSTEM_PROMPT + "\n" + history_text + "AI:"

    # Hugging Face Router API call
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 300}
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        if response.status_code != 200:
            return jsonify({"reply": f"AI API error: {response.text}", "session_id": session_id})

        ai_output = response.json()
        # Router returns list of dicts with 'generated_text'
        ai_reply = ai_output[0]["generated_text"] if isinstance(ai_output, list) else "Kya baat hai, reply nahi mila 😅"

        # Append Amazon or fallback web search
        if amazon_results:
            ai_reply += "\n\nHere are some options 👇\n" + "\n".join(f"• {link}" for link in amazon_results)
        elif not amazon_results:
            ai_reply += "\n\n" + "\n".join(f"• {link}" for link in web_search(user_message))

        conversations[session_id].append({"role": "ai", "content": ai_reply})
        return jsonify({"reply": ai_reply, "session_id": session_id})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed 😅: {str(e)}", "session_id": session_id})

# ------------------------------
# Home endpoint
# ------------------------------
@app.route("/", methods=["GET"])
def home():
    return "Kachra AI is live! Use POST /chat 😎"

# ------------------------------
# Run app
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
