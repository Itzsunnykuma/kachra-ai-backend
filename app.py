# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from requests.exceptions import RequestException # Import specific exception

app = Flask(__name__)
CORS(app)

# Retrieve Hugging Face token from environment variables
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    # This should be caught by Render, but keep for local testing
    raise ValueError("HF_TOKEN is not set in environment variables!")

# New Hugging Face Router URL (Correct capitalization for model ID)
HF_API_URL = "https://router.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

# Optional: Welcome message at the root URL
@app.route("/", methods=["GET"])
def home():
    return "Welcome to Kachra AI Backend! Use the POST /chat endpoint to interact with the AI.", 200

@app.route("/chat", methods=["POST"])
def chat():
    response = None # Initialize response outside try block
    try:
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"response": "Please provide a message."})

        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        # Note: Some HF models require the prompt to be nested under 'inputs', 
        # and some may prefer the OpenAI-style 'messages'. Sticking to 'inputs'.
        payload = {"inputs": prompt}

        # Increased timeout to 120s for cold starts on free tier
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=120)
        
        # This will raise an exception for HTTP error codes (401, 404, 500 etc.)
        response.raise_for_status() 
        
        result = response.json()

        # HF Router often returns a list of dicts
        if isinstance(result, list) and "generated_text" in result[0]:
            text = result[0]["generated_text"]
        else:
            text = str(result)
            
        return jsonify({"response": text})

    except RequestException as e:
        # Catch network/HTTP errors (e.g., Timeout, 401, 404)
        error_details = response.text if response is not None else "No HTTP response details."
        # Print the detailed error to your Render Logs!
        print(f"Hugging Face API Request Failed (Status: {response.status_code if response is not None else 'N/A'}): {e}. Details: {error_details}")
        
        return jsonify({
            "response": "Error connecting to AI.", 
            "error_type": "HF_API_REQUEST_FAILED", 
            "details": error_details
        }), 503

    except Exception as e:
        # Catch any other unexpected code errors
        print(f"General Error in /chat: {e}")
        return jsonify({
            "response": "An unexpected error occurred.", 
            "error_type": "GENERAL_SERVER_ERROR"
        }), 500

# Health check endpoint for Render
@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
