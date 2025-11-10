# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from requests.exceptions import RequestException # Import specific exception

app = Flask(__name__)
CORS(app)  # Allow frontend to access API

# Retrieve Hugging Face token from environment variables
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    # This should be caught by Render, but useful for local testing
    raise ValueError("HF_TOKEN is not set in environment variables!")

# New Hugging Face Router URL (Using correct capitalization for the model ID)
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

# Optional: Welcome message at the root URL
@app.route("/", methods=["GET"])
def home():
    return "Welcome to Kachra AI Backend! Use the POST /chat endpoint to interact with the AI.", 200

# The main chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    # Initialize response to None to handle potential errors before the request is made
    response = None 
    try:
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"response": "Please provide a message."})

        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
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
        # Catch network/HTTP errors (e.g., Timeout, 401, 404 from the HF API)
        status_code = response.status_code if response is not None else 'N/A'
        error_details = response.text if response is not None else "No HTTP response details."
        
        # Print the detailed error to your Render Logs!
        print(f"Hugging Face API Request Failed (Status: {status_code}): {e}. Details: {error_details}")
        
        # Return the detailed error information to the client
        return jsonify({
            "response": "Error connecting to AI.", 
            "error_type": f"HF_API_REQUEST_FAILED_HTTP_{status_code}", 
            "details": error_details
        }), 503

    except Exception as e:
        # Catch any other unexpected code errors (e.g., JSON parsing failure)
        print(f"General Error in /chat: {e}")
        return jsonify({
            "response": "An unexpected server error occurred.", 
            "error_type": "GENERAL_SERVER_ERROR",
            "details": str(e)
        }), 500

# Health check endpoint for Render
@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# Run the app on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
