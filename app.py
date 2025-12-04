from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
import requests

app = Flask(__name__)
CORS(app)

# -----------------------------
# Groq API Key
# -----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set!")

client = Groq(api_key=GROQ_API_KEY)

# -----------------------------
# SerpAPI Key for web search
# -----------------------------
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# -----------------------------
# Personality Prompt
# -----------------------------
personality_prompt = (
    "You are Kachra AI. Be clear, helpful, and funny like an Indian best friend. "
    "For casual chats like greetings, reply in 1–2 lines max unless the user asks to write an email. "
    "Use Hinglish with memes casually but stay professional for tasks. "
    "If asked about the creator → reply: 'Kachra AI was created by Sunny.'"
)

# -----------------------------
# Session storage (short memory)
# -----------------------------
sessions = {}
MAX_MEMORY = 5  # store last 5 messages per session


# -----------------------------
# Web Search
# -----------------------------
def search_web(query, num_results=3):
    if not SERPAPI_KEY:
        return "Web search not available. SERPAPI_KEY not set."

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": query, "num": num_results, "api_key": SERPAPI_KEY},
            timeout=10
        ).json()

        results = response.get("organic_results", [])
        if not results:
            return "No search results found."

        return "\n".join([f"- {r.get('title', '')}: {r.get('link', '')}" for r in results[:num_results]])

    except Exception as e:
        return f"Error while searching the web: {e}"


# -----------------------------
# Chat Endpoint
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Create fresh session memory for new session_id
        if session_id not in sessions:
            sessions[session_id] = []

        # Check for web search request
        if user_message.lower().startswith("search:"):
            query = user_message.replace("search:", "").strip()
            result = search_web(query)
            return jsonify({"reply": result})

        # Store user message with short memory
        sessions[session_id].append({"role": "user", "content": user_message})
        sessions[session_id] = sessions[session_id][-MAX_MEMORY:]

        # Groq Completion
        response = client.chat.completions.create(
            model="groq/compound",
            messages=[{"role": "system", "content": personality_prompt}] + sessions[session_id],
            temperature=0.6,
            max_tokens=300,
        )

        reply = response.choices[0].message.content

        # Short, 1–2 line replies unless writing an email
        if "email" not in user_message.lower():
            reply = " ".join(reply.split()[:25])  # approx 1–2 lines

        # Store assistant reply
        sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
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
