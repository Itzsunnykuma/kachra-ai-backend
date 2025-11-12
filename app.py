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

# Hugging Face Router API endpoint
HF_API_URL = "https://router.huggingface.co/hf-inference"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"response": "Please provide a message."})

        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
    "model": "meta-llama/Meta-Llama-3-8B",
    "inputs": prompt
}

        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()
        print("HF API response:", result)  # For debugging

        # Improved response parsing
        if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
            text = result[0]["generated_text"]
        elif isinstance(result, dict) and "generated_text" in result:
            text = result["generated_text"]
        elif isinstance(result, dict) and "error" in result:
            text = f"Error from Hugging Face: {result['error']}"
        else:
            text = str(result)

        return jsonify({"response": text})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Error connecting to AI."})

# Optional health check
@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# Run the app on Render or locally
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
