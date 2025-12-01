from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os

app = Flask(__name__)
CORS(app)

# -----------------------------
# Groq API Key (required)
# -----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set!")

client = Groq(api_key=GROQ_API_KEY)

# -----------------------------
# Personality Prompt
# -----------------------------
personality_prompt = (
    "You are Kachra AI. Be clear, structured, helpful and funny like an Indian best friend. "
    "Use casual Hinglish causally and funny trending memes to entertain within messages. Professional tone for tasks. "
    "If asked about the creator/owner/developer of Kachra AI → reply: 'Kachra AI was created by Sunny.'"
)

# -----------------------------
# Chat Endpoint
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Force the use of groq/compound model
        model_name = "groq/compound"
        print(f"Using model: {model_name}")

        # Groq Chat Completion
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": personality_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.6,
            max_tokens=1024
        )

        # -----------------------------
        # DEBUG: print the full response
        # -----------------------------
        print("Full Groq Response:", response)

        # Extract reply safely
        reply = response.choices[0].message.content
        print("Extracted Reply:", reply)

        return jsonify({"reply": reply})

    except Exception as e:
        # Log exception
        print("Error in /chat endpoint:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Root endpoint
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Kachra AI backend running successfully!"})

# -----------------------------
# Start server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
