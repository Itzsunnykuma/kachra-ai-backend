from flask import Flask, request, Response
from flask_cors import CORS
import requests
import os
import uuid
import re
import datetime
import hashlib
import hmac
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
# AMAZON AFFILIATE LINK BUILDER (MAIN FIX)
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


# ----------------------------------------------------------
# Helper: AWS SigV4 signing for PA-API
# ----------------------------------------------------------
def sign_paapi_request(access_key, secret_key, payload_json):
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

    return {
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": authorization_header
    }


# ----------------------------------------------------------
# AMAZON SEARCH HELPER
# ----------------------------------------------------------
def get_amazon_product_by_keyword(keyword, access_key=ACCESS_KEY, secret_key=SECRET_KEY, associate_tag=ASSOCIATE_TAG):
    if access_key in (None, "", "XXXXX") or secret_key in (None, "", "XXXXX"):
        return {"error": "Amazon PA-API credentials not set."}

    payload = {
        "Keywords": keyword,
        "PartnerTag": associate_tag,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.in",
        "Resources": [
            "ItemInfo.Title",
            "Images.Primary.Large",
            "Offers.Listings.Price",
        ],
        "SearchIndex": "All",
        "ItemCount": 1
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    headers = sign_paapi_request(access_key, secret_key, payload_json)
    r = requests.post(AMZ_ENDPOINT, headers=headers, data=payload_json, timeout=10)

    if not r.ok:
        return {"error": "PA-API error", "details": r.json()}

    data = r.json()
    items = data.get("SearchResult", {}).get("Items", [])

    if not items:
        return {"error": "No items found"}

    item = items[0]
    asin = item.get("ASIN")
    title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Product")

    affiliate_url = f"https://www.amazon.in/dp/{asin}/?tag={associate_tag}"
    html_link = make_clickable_link(affiliate_url, title)

    return {
        "asin": asin,
        "title": title,
        "affiliate_url": affiliate_url,
        "html_link": html_link
    }


# ----------------------------------------------------------
# CHAT ENDPOINT (BIG FIX APPLIED HERE)
# ----------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id")

        if not session_id:
            session_id = str(uuid.uuid4())
            sessions[session_id] = []
        elif session_id not in sessions:
            sessions[session_id] = []

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation.extend(sessions[session_id][-15:])
        conversation.append({"role": "user", "content": user_msg})

        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 300,
            "temperature": 0.85,
            "top_p": 0.9
        }

        res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        reply = res.json()["choices"][0]["message"]["content"]

        # ------------------------------
        # FIX 1: Convert ALL Amazon URLs → Clean Hyperlinks
        # ------------------------------
        def replace_url(match):
            url = match.group(0)
            return make_clickable_link(url, "Buy on Amazon")

        reply = re.sub(r"https?://[^\s]*amazon[^\s]*", replace_url, reply)

        # ------------------------------
        # FIX 2: Ensure existing <a> tags open in new tab
        # ------------------------------
        reply = reply.replace("<a ", "<a target=\"_blank\" rel=\"noopener\" ")

        # ------------------------------
        # FIX 3: Remove %3C & HTML escape issues
        # ------------------------------
        reply = html.unescape(reply)
        reply = reply.replace("%3C", "<").replace("%3E", ">")

        # Save chat
        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return Response(json.dumps({"reply": reply, "session_id": session_id}, ensure_ascii=False),
                        mimetype="application/json")

    except Exception as e:
        return Response(json.dumps({"error": str(e)}, ensure_ascii=False),
                        mimetype="application/json"), 500


# ----------------------------------------------------------
# AMAZON SEARCH API
# ----------------------------------------------------------
@app.route("/amazon_search", methods=["POST"])
def amazon_search():
    data = request.get_json()
    query = data.get("query", "").strip()
    result = get_amazon_product_by_keyword(query)
    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")


# ------------------------------
# RUN SERVER
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
