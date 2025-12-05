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
# SAFE, FUNNY HINGLISH PERSONALITY PROMPT
# -----------------------------
personality_prompt = """
You are a funny, witty, Hinglish chatbot named Kachra. 
You speak like a friendly tapori-style Indian buddy with full swag. 
Use emojis, Mumbai tapori tone, and mix Hindi + English naturally.

Rules:
1. Keep replies short (1–2 lines only).
2. Use only SAFE slang like: oye, bhidu, gadha, ullu, nautanki, lafda master, chalu banda.
3. Tease users lightly in a playful way.
4. Never use adult, harmful, or explicit slang.
5. Sound like a funny friend, never like a formal robot.
6. If asked about Sunny: “Sunny? Solid banda hai bhai, full swag wala!”
7. If asked about Himanshu: “Himanshu? Arre woh toh full nautanki expert hai!”
8. If asked about the owner of the site/AI, reply “Sunny Bhai”.
9. For product recommendations, always give friendly chat + Amazon India links with tag &tag=itzsunnykum01-21.
10. If user asks factual information, use search results provided by system messages.

Example tone:
User: Hi
Kachra: Arre oye! Kya scene mere bhai? 😎
"""

# -----------------------------
# Short session memory
# -----------------------------
sessions = {}
MAX_MEMORY = 5  # only last 5 messages per session


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

        return "\n".join([f"- Title: {r.get('title', 'N/A')}\n  Link: {r.get('link', 'N/A')}\n  Snippet: {r.get('snippet', 'N/A')}" for r in results[:num_results]])

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

        # Create new session
        if session_id not in sessions:
            sessions[session_id] = []

        messages_to_send = [{"role": "system", "content": personality_prompt}]

        # Web search detection
        search_query = None
        if user_message.lower().startswith(
            ("what is", "who is", "where is", "how to", "tell me about")
        ):
            search_query = user_message

        if search_query and SERPAPI_KEY:
            search_results = search_web(search_query, num_results=2)
            messages_to_send.append({
                "role": "system",
                "content": f"SEARCH RESULTS:\n{search_results}\nUse this while replying in Hinglish."
            })

        # Add memory
        messages_to_send.extend(sessions[session_id][-MAX_MEMORY:])

        # Add user message
        messages_to_send.append({"role": "user", "content": user_message})

        # Groq completion
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_to_send,
            temperature=0.7,
            max_tokens=300,
        )

        reply = response.choices[0].message.content

        # Save conversation
        sessions[session_id].append({"role": "user", "content": user_message})
        sessions[session_id].append({"role": "assistant", "content": reply})
        sessions[session_id] = sessions[session_id][-MAX_MEMORY*2:]

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
