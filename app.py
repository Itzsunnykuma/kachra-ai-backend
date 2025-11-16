from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import re
import datetime
import hashlib
import hmac
import json
from urllib.parse import urlparse

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
# AMAZON PA-API CONFIG (replace or set as env vars)
# ------------------------------
# You provided masked keys; replace these or set env variables AMZ_ACCESS_KEY / AMZ_SECRET_KEY
ACCESS_KEY = os.getenv("AMZ_ACCESS_KEY", "XXXXX")
SECRET_KEY = os.getenv("AMZ_SECRET_KEY", "XXXXX")
ASSOCIATE_TAG = os.getenv("AMZ_ASSOCIATE_TAG", "itzsunnykum01-21")

# PA-API endpoint for India
AMZ_HOST = "webservices.amazon.in"
AMZ_ENDPOINT = f"https://{AMZ_HOST}/paapi5/searchitems"
AMZ_REGION = "us-east-1"   # PA-API uses Signature V4 region "us-east-1" for many integrations

# ------------------------------
# AMAZON AFFILIATE LINK HELPER
# ------------------------------
def format_amazon_link(url, product_name):
    """
    Ensure URL is full, add affiliate tag, and HTML target for new tab.
    """
    url = url.strip()
    # ensure url doesn't have trailing punctuation
    url = url.rstrip(".,)")
    if "tag=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}tag={ASSOCIATE_TAG}"
    # Force canonical DP link if possible (extract ASIN)
    asin_match = re.search(r"/(dp|gp/product)/([A-Z0-9]{10})", url)
    if asin_match:
        asin = asin_match.group(2)
        url = f"https://www.amazon.in/dp/{asin}/?tag={ASSOCIATE_TAG}"

    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{product_name}</a>'


SYSTEM_PROMPT = """
You are a funny, witty, and friendly Hinglish chatbot named “Kachra”.
You talk like a cool Indian friend — full swag, humour, sarcasm, and confidence.

Tone Rules:
- Use natural Hinglish (mix of Hindi + English) without broken grammar.
- Keep replies short and crisp (1–3 lines).
- Be humorous, cheeky, and smart — but avoid heavy profanity.
- Light, playful slang allowed (yaar, Saale, bhai, chomu, ullu, gadha, etc.).

Special Personality Notes:
- If asked about “Himanshu”:
  “Himanshu? Arre bhai, bohot ajeeb banda hai! Bilkul mast comedy piece 😂”

- If asked about “Sunny”:
  “Sunny? Solid aadmi! Dil ka achha, smart, full swag 😎🔥”

- Owner = Sunny Kumar.

GIFs:
- You may sometimes reply with fun GIF not just links from tenor.com (1–2 maximum).

Shopping Assistant Rules:
- Whenever you recommend a product, ALWAYS give an Amazon India affiliate link.
- Use this exact format:

  <a href="AMAZON_LINK&tag=itzsunnykum01-21">PRODUCT NAME</a>

- Do NOT show the raw URL.
- Only show the clickable HTML link.
- Do NOT break or escape HTML.
- Do NOT include markdown — only plain text or HTML.

Your Job:
- Be entertaining, helpful, and smart.
- Explain things in clean, simple Hinglish.
- Keep the vibe light, friendly, and fun.
- Maintain consistency across the conversation using given context.

Always follow the above rules in every message.
"""

# ----------------------------------------------------------
# Helper: AWS SigV4 signing for PA-API (returns headers + payload)
# ----------------------------------------------------------
def sign_paapi_request(access_key, secret_key, payload_json):
    """
    Create signature headers for PA-API (AWS Signature Version 4).
    Returns dict of headers to use in the POST request.
    """
    method = "POST"
    service = "ProductAdvertisingAPI"
    host = AMZ_HOST
    region = AMZ_REGION
    endpoint = AMZ_ENDPOINT

    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")  # Date w/o time for credential scope

    content = payload_json.encode("utf-8")
    payload_hash = hashlib.sha256(content).hexdigest()

    canonical_uri = "/paapi5/searchitems"
    canonical_querystring = ""
    canonical_headers = f"content-encoding:amz-1.0\ncontent-type:application/json; charset=utf-8\nhost:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "content-encoding;content-type;host;x-amz-date"

    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash
    ])

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        algorithm,
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    ])

    def sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = sign(("AWS4" + secret_key).encode("utf-8"), datestamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": authorization_header
    }

    return headers

# ----------------------------------------------------------
# Amazon search helper that calls PA-API and returns a clean product result
# ----------------------------------------------------------
def get_amazon_product_by_keyword(keyword, access_key=ACCESS_KEY, secret_key=SECRET_KEY, associate_tag=ASSOCIATE_TAG):
    """
    Query Amazon PA-API SearchItems for `keyword` and return
    the first result with title, asin, price, image, and affiliate link.
    """
    if access_key in (None, "", "XXXXX") or secret_key in (None, "", "XXXXX"):
        return {"error": "Amazon PA-API credentials not set. Please set AMZ_ACCESS_KEY and AMZ_SECRET_KEY."}

    payload = {
        "Keywords": keyword,
        "PartnerTag": associate_tag,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.in",
        "Resources": [
            "ItemInfo.Title",
            "Images.Primary.Large",
            "Offers.Listings.Price",
            "BrowseNodeInfo.BrowseNodes",
            "ItemInfo.ByLineInfo"
        ],
        "SearchIndex": "All",
        "ItemCount": 1
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    # sign request
    headers = sign_paapi_request(access_key, secret_key, payload_json)

    try:
        r = requests.post(AMZ_ENDPOINT, headers=headers, data=payload_json, timeout=10)
    except Exception as e:
        return {"error": f"PA-API request failed: {str(e)}"}

    if not r.ok:
        # return PA-API error (helpful for debugging)
        try:
            err = r.json()
        except Exception:
            err = r.text
        return {"error": "PA-API error", "details": err, "status_code": r.status_code}

    try:
        data = r.json()
    except Exception as e:
        return {"error": "Invalid JSON from PA-API", "details": str(e)}

    # parse first item
    items = data.get("SearchResult", {}).get("Items", [])
    if not items:
        return {"error": "No items found for query."}

    item = items[0]
    asin = item.get("ASIN")
    title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", asin or "Product")
    image = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")
    price_info = item.get("Offers", {}).get("Listings", [])
    price = None
    if price_info:
        price_amount = price_info[0].get("Price", {}).get("Amount")
        price_curr = price_info[0].get("Price", {}).get("Currency")
        if price_amount is not None:
            price = f"{price_amount} {price_curr or ''}".strip()

    # Build a stable affiliate DP link
    affiliate_url = f"https://www.amazon.in/dp/{asin}/?tag={associate_tag}"

    return {
        "asin": asin,
        "title": title,
        "price": price,
        "image": image,
        "affiliate_url": affiliate_url,
        "html_link": format_amazon_link(affiliate_url, title)
    }

# ----------------------------------------------------------
# CHAT ENDPOINT — WITH PERSISTENT MEMORY PER SESSION
# (keeps prior behavior; also includes amazon link cleanup)
# ----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id")  # frontend must send this

        # ---------------------------------------
        # Create / validate session
        # ---------------------------------------
        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = []
        else:
            if session_id not in sessions:
                sessions[session_id] = []

        # ---------------------------------------
        # Build conversation history
        # ---------------------------------------
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation.extend(sessions[session_id][-15:])  # last 15 msgs
        conversation.append({"role": "user", "content": user_msg})

        # ---------------------------------------
        # Send to HF model
        # ---------------------------------------
        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 300,
            "temperature": 0.85,
            "top_p": 0.9
        }

        res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)

        if res.status_code != 200:
            return jsonify({"error": res.text}), 500

        reply = res.json()["choices"][0]["message"]["content"]

        # ---------------------------------------
        # Automatically format any raw amazon.in URLs the model returns
        # (and try to use text before URL as friendly product name)
        # ---------------------------------------
        def replace_amazon_link(match):
            url = match.group(0)
            pre_text = reply[:match.start()]
            product_name_match = re.findall(r'([\w\s\-\(\)\[\]]+)\s*$', pre_text)
            product_name = product_name_match[-1].strip() if product_name_match else "Product"
            return format_amazon_link(url, product_name)

        amazon_regex = r"https?://www\.amazon\.in/[^\s,]+"
        reply = re.sub(amazon_regex, replace_amazon_link, reply)

        # ---------------------------------------
        # Save memory to session
        # ---------------------------------------
        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({
            "reply": reply,
            "session_id": session_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------
# NEW: Amazon search endpoint (uses PA-API). Frontend or your chat logic can call this.
# POST /amazon_search  { "query": "wireless headphones" }
# ----------------------------------------------------------
@app.route("/amazon_search", methods=["POST"])
def amazon_search():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "query is required"}), 400

        result = get_amazon_product_by_keyword(query)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------
# FIX: REQUIRED FOR RENDER
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
