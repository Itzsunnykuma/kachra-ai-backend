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
# AMAZON AFFILIATE LINK HELPER
# ------------------------------
def format_amazon_link(url, product_name):
    if not url:
        return ""

    url = url.strip()
    url = url.rstrip(".,)")

    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    if asin_match:
        asin = asin_match.group(1)
        url = f"https://www.amazon.in/dp/{asin}/?tag={ASSOCIATE_TAG}"
    else:
        separator = "&" if "?" in url else "?"
        if "tag=" not in url:
            url = f"{url}{separator}tag={ASSOCIATE_TAG}"

    safe_name = html.escape(product_name)
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{safe_name}</a>'


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
<a href="AMAZON_LINK&tag=itzsunnykum01-21">PRODUCT NAME</a>

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

    headers = {
        "Content-Encoding": "amz-1.0",
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": authorization_header
    }

    return headers


# ----------------------------------------------------------
# Amazon search helper
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
            "BrowseNodeInfo.BrowseNodes",
            "ItemInfo.ByLineInfo"
        ],
        "SearchIndex": "All",
        "ItemCount": 1
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    headers = sign_paapi_request(access_key, secret_key, payload_json)

    try:
        r = requests.post(AMZ_ENDPOINT, headers=headers, data=payload_json, timeout=10)
    except Exception as e:
        return {"error": f"PA-API request failed: {str(e)}"}

    if not r.ok:
        try:
            err = r.json()
        except:
            err = r.text
        return {"error": "PA-API error", "details": err, "status": r.status_code}

    try:
        data = r.json()
    except Exception as e:
        return {"error": "Invalid JSON", "details": str(e)}

    items = data.get("SearchResult", {}).get("Items", [])
    if not items:
        return {"error": "No items found"}

    item = items[0]
    asin = item.get("ASIN")
    title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", asin or "Product")
    image = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")

    price_info = item.get("Offers", {}).get("Listings", [])
    price = None
    if price_info:
        p = price_info[0].get("Price", {})
        if p.get("Amount"):
            price = f"{p['Amount']} {p.get('Currency', '')}"

    affiliate_url = f"https://www.amazon.in/dp/{asin}/?tag={associate_tag}"
    html_link = format_amazon_link(affiliate_url, title)

    return {
        "asin": asin,
        "title": title,
        "price": price,
        "image": image,
        "affiliate_url": affiliate_url,
        "html_link": html_link
    }


# ----------------------------------------------------------
# CHAT ENDPOINT
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
        else:
            if session_id not in sessions:
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
        if res.status_code != 200:
            return Response(json.dumps({"error": res.text}, ensure_ascii=False), mimetype="application/json"), 500

        reply = res.json()["choices"][0]["message"]["content"]

        # ------------------------------
        # CLEAN AMAZON LINKS
        # ------------------------------
        def repl(match):
            url = match.group(0)
            return format_amazon_link(url, "Product")

        reply = re.sub(r"https?://www\.amazon\.in/[^\s,]+", repl, reply)

        # ------------------------------
        # FINAL HTML UNESCAPE FIX
        # ------------------------------
        reply = html.unescape(reply)
        reply = reply.replace("%3C", "<").replace("%3E", ">")

        sessions[session_id].append({"role": "user", "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return Response(json.dumps({"reply": reply, "session_id": session_id}, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        return Response(json.dumps({"error": str(e)}, ensure_ascii=False), mimetype="application/json"), 500


# ----------------------------------------------------------
# Amazon Search API
# ----------------------------------------------------------
@app.route("/amazon_search", methods=["POST"])
def amazon_search():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return Response(json.dumps({"error": "query is required"}, ensure_ascii=False), mimetype="application/json"), 400

        result = get_amazon_product_by_keyword(query)
        return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")

    except Exception as e:
        return Response(json.dumps({"error": str(e)}, ensure_ascii=False), mimetype="application/json"), 500


# ------------------------------
# RUN SERVER
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
