from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)   # <-- IMPORTANT for InfinityFree / external frontend

HF_TOKEN = os.getenv("HF_TOKEN", "your_huggingface_write_token")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
API_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like an Indian friend with swag and humour.
Use Hinglish, desi words, insults, emojis.
Keep messages short and fun.
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")   # <-- frontend expects "message"

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 400,
            "temperature": 0.9
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code != 200:
            return jsonify({"error": "HF API error", "details": response.text}), 500

        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
