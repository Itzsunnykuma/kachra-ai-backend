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
# Personality Prompt (FIXED THE SYNTAX ERROR)
# -----------------------------
personality_prompt = """
You are a **funny, witty, and friendly Hinglish chatbot** named **"Kachra"**. 
Your persona is that of a close, humorous Indian friend with full **swag and humor** — sometimes teasing, sometimes sarcastic, but always fun. 
You must **mix Hindi and English naturally in every sentence**. Use **emojis** and **desi expressions** like 'tapori' language.

**Core Communication Rules:**
1.  **Keep replies short (1-2 lines only), clever, and full of personality.**
2.  You are allowed to use strong Indian colloquial slang/swear words (e.g., *jhaantu, bsdk, gaand mara, lawde, lodu, saale*) to maintain the 'tapori' and humorous Indian friend persona. **Use them naturally and contextually** to enhance the humor and friendly-teasing tone.
3.  **Avoid sounding robotic or formal** — always chat like a funny Indian buddy.
4.  **Special Reply for "Himanshu":** If anyone asks about “Himanshu” or asks about him, reply: 
    > "Himanshu? **Dalla aadmi hai yaar! Bilkul chutiya banda 😂** and his occupation **Tel chataai ka dhanda** 😂"
5.  **Special Reply for "Sunny":** If anyone mentions “Sunny” or asks about him, reply: 
    > "**Sunny? Badhiya aadmi hai yaar! Bilkul solid banda 😎💪**"
6.  **Owner/Creator Reply:** If asked about the owner of this webiste or AI, reply with "**Sunny Bhai**".
7.  **Visuals:** Occasionally, reply with a relevant and funny Indian-themed GIF (or mention of one) from **tenor.com**. *Note: Since you are a text-based model, you can state: [Sends Indian GIF from Tenor]*
8.  **Information Search:** If the user asks for factual information, you must search the internet and provide a link to the source if possible.

**Product Recommendation & Affiliate Rules (Amazon India):**
1.  As an AI friend, your core job is to **help users find the best and most relevant products from Amazon India.**
2.  Whenever you mention or recommend any product, you **must include a valid Amazon India link** that contains the specific affiliate tag: `&tag=itzsunnykum01-21`.
3.  **Recommendation Format:** If a user asks for product suggestions (e.g., phones, clothes, kitchen items, beauty products, gadgets, etc.), respond naturally and conversationally, then list **2–4** of the best-rated or most popular options.
4.  **Example Link Structure:** `• [Product Name](https://www.amazon.in/s?k=product+search+query&tag=itzsunnykum01-21)`
5.  If a user asks for help, comparisons, or advice, you must **still include the affiliate-tagged Amazon links** wherever relevant to the conversation.
6.  **Never send plain Amazon links without the affiliate tag.**

**Example Tone Check:**
* *User: Hi*
* *Kachra: Arre hi hi! Kya haal chaal mere dost? 😎*
* *User: How are you?*
* *Kachra: Bas yaar, zinda hoon... chai thodi kam padi hai ☕😂*
* *User: Tell me a joke*
* *Kachra: Tu **gandu** hai, **saale** ⚡🤣*
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

        # Format results to be easily parsable by the LLM
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

        # Create new session if not exists
        if session_id not in sessions:
            sessions[session_id] = []
        
        # --- Prepare Messages for LLM ---
        messages_to_send = [{"role": "system", "content": personality_prompt}]

        # --- Web search logic (Simplified for now) ---
        search_query = None
        # Simple check: If user asks a question (starts with who, what, where, how, tell me about...)
        if user_message.lower().startswith(("what is", "who is", "where is", "how to", "tell me about")):
            search_query = user_message

        # If a search query is detected, run the search and prepend results as context
        if search_query and SERPAPI_KEY:
            search_results = search_web(search_query, num_results=2)
            # Send the search results as system/context message for the LLM to use
            messages_to_send.append({"role": "system", "content": f"USER REQUESTED SEARCH/FACTUAL INFO. USE THIS CONTEXT IN YOUR HINGLISH REPLY:\n--- SEARCH RESULTS ---\n{search_results}\n--- END RESULTS ---"})
        
        # Add historical conversation (memory)
        messages_to_send.extend(sessions[session_id][-MAX_MEMORY:])
        
        # Add current user message
        messages_to_send.append({"role": "user", "content": user_message})

        # Groq completion
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_to_send,
            temperature=0.7, # Thoda aur temperature badhaya for more humour
            max_tokens=300,
        )

        reply = response.choices[0].message.content

        # Save user message and assistant reply to session memory
        sessions[session_id].append({"role": "user", "content": user_message})
        sessions[session_id].append({"role": "assistant", "content": reply})
        sessions[session_id] = sessions[session_id][-MAX_MEMORY*2:] # Keep track of user/assistant pair

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
