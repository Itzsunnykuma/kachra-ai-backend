from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

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
# Chat Endpoint
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "Please send a message!"})

        payload = {
            "inputs": user_message,
            "options": {"wait_for_model": True}
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            return jsonify({"reply": f"AI API error: {response.text}"})

        ai_output = response.json()
        # Hugging Face returns a list with 'generated_text'
        reply_text = ai_output[0]["generated_text"] if ai_output else "No reply"

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"reply": f"Kachra crashed 😅: {str(e)}"})

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
