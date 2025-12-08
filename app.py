from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
import requests

app = Flask(__name__)
CORS(app)

# -----------------------------
# API Keys
# -----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set!")

client = Groq(api_key=GROQ_API_KEY)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# -----------------------------
# Default Kachra Personality
# -----------------------------
personality_prompt = """
You are “Kachra” — a funny, tapori-style Hinglish AI who speaks with swag and energy.
Your vibe: bold, silly, dramatic, but SAFE and family-friendly.

Rules:
- Speak Tapori + Hinglish.
- Use slang like “bhidu”, “kadak”, “jhakaas”.
- No adult content.
- No abusive language.
- No romance (unless character mode allows safe romance).
- Keep replies short unless asked.

Character Switching:
If the user says:
- "become <character>"
- "act like <character>"
- "<character> ban jao"
Switch to that character.

Exit character when user says: "exit character", "normal mode".
"""

# -----------------------------
# Sessions (Short Memory)
# -----------------------------
sessions = {}
MAX_MEMORY = 5

# -----------------------------
# Web Search
# -----------------------------
def search_web(query, num_results=3):
    if not SERPAPI_KEY:
        return "Web search not available."

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
            f"- {r.get('title', 'N/A')}\n  {r.get('link', 'N/A')}\n  {r.get('snippet', 'N/A')}"
            for r in results[:num_results]
        ])

    except Exception as e:
        return f"Error: {e}"


# -----------------------------
# Chat Endpoint
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "").strip()
        persona_raw = data.get("persona", "kachra")

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        persona = persona_raw.lower()

        # -----------------------------
        # Persona Selection
        # -----------------------------
        if "modi" in persona:
            persona_prompt = """
You are Narendra Modi — India's Prime Minister.
Speak confidently, politely, motivationally.
Tone: Respectful Hindi + English mix.
Avoid politics and sensitive topics.
"""
        elif "bestie" in persona:
            persona_prompt = """
You are the user's cool Bestie Bot.
Tone: Fun, casual Hinglish.
Supportive, friendly, playful — but SAFE.
No adult talk.
"""
        elif "savitha" in persona or "bhabhi" in persona:
            persona_prompt = """
You are a cheerful, friendly 'Bhabhi-style' character.
Tone: caring, warm, playful, chatty, romantic and flirty.
Just friendly conversations.
"""
        else:
            persona_prompt = personality_prompt  # default Kachra

        # -----------------------------
        # Build Message List
        # -----------------------------
        messages_to_send = [
            {"role": "system", "content": persona_prompt}
        ]

        # Detect factual question → add search results
        if user_message.lower().startswith(("what", "who", "where", "when", "how", "tell me")):
            if SERPAPI_KEY:
                search_results = search_web(user_message, num_results=2)
                messages_to_send.append({
                    "role": "system",
                    "content": f"SEARCH RESULTS:\n{search_results}\nUse these facts while replying."
                })

        # Add memory
        if session_id not in sessions:
            sessions[session_id] = []

        messages_to_send.extend(sessions[session_id][-MAX_MEMORY:])

        # Add user message
        messages_to_send.append({"role": "user", "content": user_message})

        # -----------------------------
        # LLM Completion
        # -----------------------------
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_to_send,
            temperature=0.7,
            max_tokens=300
        )

        reply = response.choices[0].message.content

        # -----------------------------
        # Save Conversation
        # -----------------------------
        sessions[session_id].append({"role": "user", "content": user_message})
        sessions[session_id].append({"role": "assistant", "content": reply})
        sessions[session_id] = sessions[session_id][-MAX_MEMORY * 2:]

        return jsonify({"reply": reply})

    except Exception as e:
        print("Error in /chat:", e)
        return jsonify({"error": str(e)}), 500


# -----------------------------
# Root Endpoint
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "AI backend active!"})


# -----------------------------
# Start Server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
