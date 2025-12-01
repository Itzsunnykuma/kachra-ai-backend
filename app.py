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
SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # Get from https://serpapi.com
if not SERPAPI_KEY:
    print("Warning: SERPAPI_KEY not set. Web search will not work.")

# -----------------------------
# Personality Prompt
# -----------------------------
personality_prompt = (
    "You are Kachra AI. Be clear, helpful, and funny like an Indian best friend. "
    "For casual chats like greetings, reply in 1-2 lines max. "
    "Use Hinglish and trending Indian memes for casual tone. "
    "Professional tone for tasks. "
    "Do NOT explain CPU or internal workings. "
    "If asked about the creator → reply: 'Kachra AI was created by Sunny.'"
)

# -----------------------------
# Session storage
# -----------------------------
sessions = {}

# -----------------------------
# Function to search the web
# -----------------------------
def search_web(query, num_results=3):
    if not SERPAPI_KEY:
        return "Web search not available. SERPAPI_KEY not set."

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10).json()
        results = response.get("organic_results", [])
        if not results:
            return "No search results found."
        
        search_output = ""
        for r in results[:num_results]:
            title = r.get("title", "")
            link = r.get("link", "")
            search_output += f"- {title}: {link}\n"
        return search_output
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

        # Initialize session
        if session_id not in sessions:
            sessions[session_id] = []

        # Check if user wants web search
        if user_message.lower().startswith("search:"):
            query = user_message[len("search:"):].strip()
            web_results = search_web(query)
            sessions[session_id].append({"role": "user", "content": user_message})
            sessions[session_id].append({"role": "assistant", "content": web_results})
            return jsonify({"reply": web_results})

        # Add user message to session
        sessions[session_id].append({"role": "user", "content": user_message})

        # Groq Chat Completion
        response = client.chat.completions.create(
            model="groq/compound",
            messages=[{"role": "system", "content": personality_prompt}] + sessions[session_id],
            temperature=0.6,
            max_tokens=1024
        )

        reply = response.choices[0].message.content
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
