# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)  # Allow frontend to access API

# Retrieve Hugging Face token from environment variables
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN is not set in environment variables!")

# Model URL (example: Meta LLaMA)
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/meta-llama-3-8b-instruct"

@app.route("/chat", methods=["POST"])
def chat():
    try:   # <-- this line should be **exactly 4 spaces** from the def
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"response": "Please provide a message."})

        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt}

        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()

        # Hugging Face returns either a dict or a list depending on model
        if isinstance(result, list) and "generated_text" in result[0]:
            text = result[0]["generated_text"]
        elif isinstance(result, dict) and "generated_text" in result:
            text = result["generated_text"]
        else:
            text = str(result)

        return jsonify({"response": text})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Error connecting to AI."})

# Run the app on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
