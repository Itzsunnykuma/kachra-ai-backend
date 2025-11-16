from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import re

app = Flask(__name__)
CORS(app)

# ------------------------------
# SESSION MEMORY STORAGE
# ------------------------------
sessions = {}   # { session_id: [ {role, content}, ... ] }

HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def format_amazon_link(url, product_name):
    url = url.strip()
    if "tag=itzsunnykum01-21" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}tag=itzsunnykum01-21"
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{product_name}</a>'

SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like a cool Indian friend — full swag, humour, sarcasm, and confidence.

Tone Rules:
- Use natural Hinglish (mix of Hindi + English) without broken grammar.
- Keep replies short and crisp (1–3 lines).
- Be humorous, cheeky, and smart — but avoid heavy profanity.
- Light, playful slang allowed (yaar, Saale, bhai, chomu, ullu, gadha, etc.).

Special Personality Notes:
- If asked about “Himanshu”: 
  “Himanshu? Arre bhai, bohot ajeeb banda hai! Bilkul mast comedy piece 😂”

- If asked about “Sunny”:
  “Sunny? Solid aadmi! Dil ka achha, smart, full swag 😎🔥”

- Owner = Sunny Kumar.

GIFs:
- You may sometimes reply with fun GIF, not links from tenor.com (1–2 maximum).

Shopping Assistant Rules:
- Whenever you recommend a product, ALWAYS give an Amazon India affiliate link.
- Use this exact format:

  <a href="AMAZON_LINK&tag=itzsunnykum01-21">PRODUCT NAME</a>

- Do NOT show raw URL.
- Only clickable HTML link.
- No markdown.

Always follow the above rules.
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id")

        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = []
        else:
            if session_id not in sessions:
                sessions[session_id] = []

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation.extend(sessions[session_id][-15:])
        conversation.append({"role": "user", "content": user_msg})

        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 300,
            "temperature": 0.85,
            "top_p": 0.9
        }

        res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)

        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        reply = res.json()["choices"][0]["message"]["content"]

        def replace_amazon_link(match):
            url = match.group(0)
            pre_text = reply[:match.start()]
            product_name_match = re.findall(r'([\w\s\-\(\)\[\]]+)\s*$', pre_text)
            product_name = product_name_match[-1].strip() if product_name_match else "Product"
            return format_amazon_link(url, product_name)

        amazon_regex = r"https?://www\.amazon\.in/[^\s,]+"
        reply = re.sub(amazon_regex, replace_amazon_link, reply)

        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply, "session_id": session_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# FIX: REQUIRED FOR RENDER
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
