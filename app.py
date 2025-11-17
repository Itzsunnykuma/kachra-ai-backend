from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import re
import datetime
import hashlib
import json
import html

app = Flask(__name__)
CORS(app)

# ------------------------------
# SESSION MEMORY STORAGE
# ------------------------------
sessions = {}   # { session_id: [ {role, content}, ... ] }

HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# AMAZON PA-API CONFIG
# ------------------------------
ACCESS_KEY = os.getenv("AMZ_ACCESS_KEY", "XXXXX")
SECRET_KEY = os.getenv("AMZ_SECRET_KEY", "XXXXX")
ASSOCIATE_TAG = os.getenv("AMZ_ASSOCIATE_TAG", "itzsunnykum01-21")

AMZ_HOST = "webservices.amazon.in"
AMZ_ENDPOINT = f"https://{AMZ_HOST}/paapi5/searchitems"
AMZ_REGION = "us-east-1"

# ------------------------------
# AMAZON AFFILIATE LINK BUILDER
# ------------------------------
def make_clickable_link(url, product_name="Buy on Amazon"):
    """Convert any Amazon link into a clean <a> tag hyperlink."""
    if not url:
        return url

    url = url.strip().rstrip(".,)")

    # Detect ASIN
    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    if asin_match:
        asin = asin_match.group(1)
        final_url = f"https://www.amazon.in/dp/{asin}/?tag={ASSOCIATE_TAG}"
    else:
        # If no ASIN, just append tag safely
        final_url = url
        sep = "&" if "?" in final_url else "?"
        if "tag=" not in final_url:
            final_url += f"{sep}tag={ASSOCIATE_TAG}"

    return f'<a href="{final_url}" target="_blank" rel="noopener">{product_name}</a>'

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
# LIVE NEWS FACT-CHECKING FUNCTIONS
# ------------------------------
SEARCH_API_KEY = os.getenv('SERPAPI_KEY', None)  # Replace with your API key
SEARCH_API_URL = 'https://serpapi.com/search.json'

def fact_check_news(query, max_results=3):
    """Searches live news sources for claims and returns summarized info with citations."""
    if not SEARCH_API_KEY:
        return "Fact-checking not enabled. API key missing."

    params = {
        'engine': 'google',
        'q': query,
        'api_key': SEARCH_API_KEY,
        'tbm': 'nws',  # news search
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

        if summaries:
            return "<br>".join(summaries)
        else:
            return "No credible sources found for this claim."
    except Exception as e:
        return f"Error during fact-checking: {str(e)}"

def is_fact_check_query(user_input):
    """Detects if the query is a news verification/fact-check request"""
    triggers = ['kya sach', 'verify', 'fact check', 'sahi hai', 'sach hai']
    return any(trigger in user_input.lower() for trigger in triggers)

# ------------------------------
# SESSION HANDLING FIX
# ------------------------------
def get_session(session_id=None):
    """Ensures session persists even after refresh."""
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = []
    return session_id, sessions[session_id]

# ------------------------------
# AMAZON PA-API SIGNING (EXISTING)
# ------------------------------
def sign_paapi_request(access_key, secret_key, payload_json):
    # Existing signing logic...
    method = "POST"
    service = "ProductAdvertisingAPI"
    host = AMZ_HOST
    region = AMZ_REGION

    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")

    content = payload_json.encode("utf-8")
    payload_hash = hashlib.sha256(content).hexdigest()

    canonical_uri = "/paapi5/searchitems"
    canonical_querystring = ""
    canonical_headers = (
        "content-encoding:amz-1.0\n"
        "content-type:application/json; charset=utf-8\n"
        f"host:{host}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date"

    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash
    ])
    return canonical_request

# ------------------------------
# CHAT ENDPOINT
# ------------------------------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    session_id = data.get('session_id')

    session_id, session_memory = get_session(session_id)

    # Ensure system prompt is always first
    if not any(m['role'] == 'system' for m in session_memory):
        session_memory.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Fact-check handling only if API key exists
    if is_fact_check_query(user_input) and SEARCH_API_KEY:
        fact_result = fact_check_news(user_input)
        session_memory.append({'role': 'assistant', 'content': fact_result})
        return jsonify({'session_id': session_id, 'response': fact_result})

    # HuggingFace payload (safe)
    payload = {
        "model": MODEL,
        "messages": session_memory + [{"role": "user", "content": user_input}],
        "max_tokens": 500,
        "temperature": 0.7
    }
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        resp_json = resp.json()
        reply = resp_json['choices'][0]['message']['content']
    except Exception as e:
        reply = f"Error generating response: {str(e)}"

    session_memory.append({'role': 'assistant', 'content': reply})
    return jsonify({'session_id': session_id, 'response': reply})

# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
