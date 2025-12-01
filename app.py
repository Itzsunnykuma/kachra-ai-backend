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
client = Groq(api_key=GROQ_API_KEY)

# -----------------------------
# Personality Prompt
# -----------------------------
personality_prompt = (
    "You are Kachra AI. Be clear, structured, helpful and Funny like an indian best friend. "
    "Use Hinglish when user is casual. Professional tone for tasks. "
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

        # Groq Completion using groq/compound
        response = client.chat.completions.create(
            model="groq/compound",
            messages=[
                {"role": "system", "content": personality_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.6,
            max_tokens=1024
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
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
