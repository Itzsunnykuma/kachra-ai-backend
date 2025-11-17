from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import re

app = Flask(__name__)
CORS(app)

# ------------------------------
# SESSION MEMORY STORAGE
# ------------------------------
sessions = {}  # { session_id: [ {role, content}, ... ] }

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = "meta-llama/Llama-2-7b-chat-hf"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

# ------------------------------
# AMAZON AFFILIATE
# ------------------------------
ASSOCIATE_TAG = "itzsunnykum01-21"

def convert_amazon_links_to_affiliate(text):
    """
    Convert Amazon URLs in text to clickable affiliate links using product name.
    """
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def replace_link(match):
        url = match.group(0)
        if "tag=" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}tag={ASSOCIATE_TAG}"

        # Extract product name from URL
        segments = url.split("/")
        product_name = segments[-2] if len(segments) > 2 else segments[-1]
        product_name = re.sub(r"[-_]", " ", product_name)
        product_name = re.sub(r"\?.*$", "", product_name)
        product_name = product_name[:50] + "..." if len(product_name) > 50 else product_name
        return f'<a href="{url}" target="_blank" rel="noopener">{product_name}</a>'

    return re.sub(pattern, replace_link, text)

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = f"""
You are a funny, witty Hinglish chatbot named “Kachra”.
Tone:
- Natural Hinglish (NO broken Hindi/English)
- Short replies (1–3 lines)
- Funny, sarcastic, swag vibe
- Light slang allowed ("yaar", "bhai", "chomu")
- No heavy profanity

Shopping rule:
If suggesting a product, ALWAYS provide a clickable Amazon India affiliate link like this:
<a href="https://www.amazon.in/dp/B0EXAMPLE/?tag={ASSOCIATE_TAG}" target="_blank" rel="noopener">PRODUCT NAME</a>
NO markdown. Only HTML.
"""

# ------------------------------
# LIVE NEWS FACT-CHECKING (optional)
# ------------------------------
SEARCH_API_KEY = os.getenv("SERPAPI_KEY", None)
SEARCH_API_URL = "https://serpapi.com/search.json"

def fact_check_news(query, max_results=3):
    if not SEARCH_API_KEY:
        return "Fact-checking not enabled. API key missing."
    params = {
        "engine": "google",
        "q": query,
        "api_key": SEARCH_API_KEY,
        "tbm": "nws",
        "num": max_results
    }
    try:
        response = requests.get(SEARCH_API_URL, params=params, timeout=5)
        results = response.json().get("news_results", [])
        summaries = []
        for i, item in enumerate(results[:max_results]):
            title = item.get("title", "No title")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            summaries.append(f"{i+1}. {title} - {snippet} <a href='{link}' target='_blank'>Source</a>")
        return "<br>".join(summaries) if summaries else "No credible sources found for this claim."
    except Exception as e:
        return f"Error during fact-checking: {str(e)}"

def is_fact_check_query(user_input):
    triggers = ["kya sach", "verify", "fact check", "sahi hai", "sach hai"]
    return any(trigger in user_input.lower() for trigger in triggers)

# ------------------------------
# SESSION HANDLING
# ------------------------------
def get_session(session_id=None):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = []
    return session_id, sessions[session_id]

# ------------------------------
# CALL HUGGINGFACE
# ------------------------------
def call_hf(user_message, max_tokens=250):
    if not HF_TOKEN:
        return "HF_TOKEN not set. Kachra cannot reply 😢"

    payload = {
        "inputs": user_message,
        "parameters": {"max_new_tokens": max_tokens, "temperature": 0.7}
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
        resp.raise_for_status()
        resp_json = resp.json()
        if isinstance(resp_json, dict) and "generated_text" in resp_json:
            return resp_json["generated_text"]
        elif isinstance(resp_json, list) and len(resp_json) > 0:
            return resp_json[0].get("generated_text", "Hmm yaar, thoda dikkat hai, try again!")
        else:
            return "Hmm yaar, thoda dikkat hai, try again!"
    except Exception as e:
        return f"Error connecting to HF: {str(e)}"

# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")

    session_id, session_memory = get_session(session_id)

    # Ensure system prompt is first
    if not any(m["role"] == "system" for m in session_memory):
        session_memory.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Fact-check branch
    if is_fact_check_query(user_input) and SEARCH_API_KEY:
        fact_result = fact_check_news(user_input)
        session_memory.append({"role": "assistant", "content": fact_result})
        sessions[session_id] = session_memory[-8:]
        return jsonify({"session_id": session_id, "response": fact_result})

    # Build user message string for HF
    user_message = SYSTEM_PROMPT + "\n\n"
    for m in session_memory[-8:]:
        if m["role"] != "system":
            user_message += f'{m["role"].capitalize()}: {m["content"]}\n'
    user_message += f"User: {user_input}\nAssistant:"

    # Call HF
    reply = call_hf(user_message, max_tokens=250)

    # Convert Amazon links to affiliate links with product names
    reply = convert_amazon_links_to_affiliate(reply)

    # Append to session memory
    session_memory.append({"role": "assistant", "content": reply})
    sessions[session_id] = session_memory[-8:]

    return jsonify({"session_id": session_id, "response": reply})

# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
