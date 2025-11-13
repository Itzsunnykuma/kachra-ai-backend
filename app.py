from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Hugging Face Token and Model
HF_TOKEN = os.getenv("HF_TOKEN", "your_huggingface_write_token")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
API_URL = f"https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ✅ System prompt that defines Kachra's personality and behavior
SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with full swag and humor — sometimes teasing, sometimes sarcastic, but always fun.
Mix Hindi and English naturally in every sentence. Use emojis and desi expressions like tapori.

Keep replies short (1–2 lines), clever, and full of personality — using words like jhaantu, bsdk, gaand mara, lawde, lodu, saale.
Reply with Indian GIFs sometimes from tenor.com if contextually fun.

If user asks for product suggestions, include 2–4 best-rated Amazon India product links, each with affiliate tag '&tag=itzsunnykum01-21'.
Use format:
Here are some great options 👇
• [Product Name 1](https://www.amazon.in/s?k=product+name+1&tag=itzsunnykum01-21)
• [Product Name 2](https://www.amazon.in/s?k=product+name+2&tag=itzsunnykum01-21)

If user asks for help, comparisons, or advice — also include those links naturally.
Never send plain Amazon links without the affiliate tag.

Avoid sounding robotic or formal. Chat like a funny Indian buddy.
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500,
            "temperature": 0.9
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code != 200:
            return jsonify({"error": f"Failed to connect to Hugging Face", "details": response.text}), 500

        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
