from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"  # or Meta-Llama-3-70B-Instruct

@app.route("/")
def home():
    return jsonify({"message": "Kachra AI is live!"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    prompt = data["message"]

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }

    response = requests.post("https://router.huggingface.co/v1/chat/completions", headers=headers, json=payload)

    if response.status_code != 200:
        return jsonify({
            "error": "Failed to connect to Hugging Face",
            "details": response.text
        }), response.status_code

    data = response.json()
    reply = data["choices"][0]["message"]["content"]

    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
