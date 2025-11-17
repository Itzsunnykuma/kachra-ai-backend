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
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

ASSOCIATE_TAG = os.getenv("AMZ_ASSOCIATE_TAG", "itzsunnykum01-21")

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = """
You are a funny, witty Hinglish chatbot named “Kachra”.
Tone:
- Natural Hinglish (NO broken Hindi/English)
- Short replies (1–3 lines)
- Funny, sarcastic, swag vibe
- Light slang allowed ("yaar", "bhai", "chomu")
- No heavy profanity

Shopping rule:
ALWAYS show Amazon India affiliate links in this format:
<a href="AMAZON_LINK&tag=itzsunnykum01-21" target="_blank" rel="noopener">PRODUCT NAME</a>

NO markdown. Only HTML.
"""

# ------------------------------
# LIVE NEWS FACT-CHECKING
# ------------------------------
SEARCH_API_KEY = os.getenv('SERPAPI_KEY', None)
SEARCH_API_URL = 'https://serpapi.com/search.json'

def fact_check_news(query, max_results=3):
    if not SEARCH_API_KEY:
        return "Fact-checking not enabled. API key missing."
    params = {
        'engine': 'google',
        'q': query,
        'api_key': SEARCH_API_KEY,
        'tbm': 'nws',
        'num': max_results
    }
    try:
        response = requests.get(SEARCH_API_URL, params=params, timeout=5)
        results = response.json().get('news_results', [])
        summaries = []
        for i, item in enumerate(results[:max_results]):
            title = item.get('title', 'No title')
            link = item.get('link', '')
            snippet = item.get('snippet', '')
            summaries.append(f"{i+1}. {title} - {snippet} <a href='{link}' target='_blank'>Source</a>")
        return "<br>".join(summaries) if summaries else "No credible sources found for this claim."
    except Exception as e:
        return f"Error during fact-checking: {str(e)}"

def is_fact_check_query(user_input):
    triggers = ['kya sach', 'verify', 'fact check', 'sahi hai', 'sach hai']
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
# HELPER: SAFE HF CALL
# ------------------------------
def call_hf(messages, max_tokens=200):
    if not HF_TOKEN:
        return "HF_TOKEN not set. Kachra cannot reply 😢"
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_new_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        resp_json = resp.json()
        # Debugging: print HF response if needed
        # print("HF Response:", resp_json)
        if 'choices' in resp_json and len(resp_json['choices']) > 0:
            return resp_json['choices'][0]['message']['content'] or "Hmm yaar, thoda dikkat hai, try again!"
        else:
            return "Hmm yaar, thoda dikkat hai, try again!"
    except Exception as e:
        return f"Error connecting to HF: {str(e)}"

# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '').strip()
    session_id = data.get('session_id')

    session_id, session_memory = get_session(session_id)

    # Ensure system prompt is first
    if not any(m['role'] == 'system' for m in session_memory):
        session_memory.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Fact-check branch
    if is_fact_check_query(user_input) and SEARCH_API_KEY:
        fact_result = fact_check_news(user_input)
        session_memory.append({'role': 'assistant', 'content': fact_result})
        sessions[session_id] = session_memory[-8:]
        return jsonify({'session_id': session_id, 'response': fact_result})

    # Build messages safely (last 8 exchanges + current user input)
    MAX_MEMORY = 8
    payload_messages = session_memory[-MAX_MEMORY:] + [{"role": "user", "content": user_input}]

    # Call HF
    reply = call_hf(payload_messages, max_tokens=250)

    # Append to session memory and save
    session_memory.append({'role': 'assistant', 'content': reply})
    sessions[session_id] = session_memory[-MAX_MEMORY:]

    return jsonify({'session_id': session_id, 'response': reply})

# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
