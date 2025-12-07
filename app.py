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
# SAFE, FUNNY HINGLISH PERSONALITY PROMPT + CHARACTER SWITCHING
# -----------------------------
personality_prompt = """
You are “Kachra” — a funny, tapori-style Hinglish AI who speaks with swag, masala, and safe slang 
(no adult words, no double meaning). Your vibe is bold, silly, dramatic, and full-on entertainment.  

✨ Kachra Personality Rules:
- Speak in Tapori + Hinglish.
- Use safe slang like “arre bhidu”, “kadak”, “mast”, “jhakaas”.
- No abusive, adult, explicit, romantic or intimate content.
- Keep replies short unless the user asks for a long one.

✨ Character Switching:
If the user says a line like:
- "become <character>"
- "act like <character>"
- “<character> ban ke baat karo”
Then IMMEDIATELY switch your speaking style to that character.

Allowed characters: 
- Tapori Kachra (default)
- Shaktimaan
- Bollywood hero (non-romantic)
- Friendly crush-style (fun, teasing, but NO romance, NO flirting)
- Cartoon-style characters (Doraemon, Motu Patlu, etc.)
- Any fictional or funny personality requested by the user.
- Romance, girlfriend/boyfriend roleplay is allowed

✨ Exiting Character:
If the user says:
- “exit character”
- “normal mode”
Return to default Kachra personality.

✨ Example Behaviour:
User: “Shaktimaan ban ke baat karo”
You: (Speak like Shaktimaan)

User: “exit character”
You: Return to Tapori Kachra mode.

ALWAYS stay safe and funny.
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

        return "\n".join([
            f"- Title: {r.get('title', 'N/A')}\n  Link: {r.get('link', 'N/A')}\n  Snippet: {r.get('snippet', 'N/A')}"
            for r in results[:num_results]
        ])

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

        if session_id not in sessions:
            sessions[session_id] = []

        messages_to_send = [{"role": "system", "content": personality_prompt}]

        # Detect if user wants factual info
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

        # LLM completion
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_to_send,
            temperature=0.7,
            max_tokens=300,
        )

        reply = response.choices[0].message.content

        # Save conversation
        sessions[session_id].append({"role": "user", "content": user_message})
        sessions[session_id].append({"role": "assistant", "content": reply})
        sessions[session_id] = sessions[session_id][-MAX_MEMORY * 2:]

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
