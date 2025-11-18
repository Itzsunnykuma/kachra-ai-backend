from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import re
from typing import Dict, List

app = Flask(__name__)
CORS(app)

# ------------------------------
# HF CONFIG  (FIXED 👇)
# ------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")

# WORKING MODEL (no 410 errors, fully supported)
MODEL = "meta-llama/Llama-3.2-3B-Instruct"

API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ------------------------------
# MEMORY
# ------------------------------
MAX_HISTORY = 6
session_store: Dict[str, List[Dict[str, str]]] = {}

# ------------------------------
# SYSTEM PROMPT
# ------------------------------
SYSTEM_PROMPT = """You are Kachra 😂 — a funny, savage Hinglish Indian friend.
Reply only in short 1–2 line witty Hinglish messages.
"""

ASSOCIATE_TAG = "itzsunnykum01-21"

# ------------------------------
# HELPERS
# ------------------------------
def convert_amazon_links(text):
    pattern = r"https?://www\.amazon\.in/[^\s<>]+"

    def rep(match):
        url = match.group(0)
        if "tag=" not in url:
            url += ("&" if "?" in url else "?") + f"tag={ASSOCIATE_TAG}"
        name = url.split("/")[-2].replace("-", " ")
        name = re.sub(r"\?.*$", "", name)
        return f'<a href="{url}" target="_blank">{name}</a>'

    return re.sub(pattern, rep, text)


def clean(t):
    if not isinstance(t, str):
        return "Error 😅"
    return t.replace("\u0000", "").strip()


def build_prompt(history: List[Dict[str, str]]) -> str:
    final = SYSTEM_PROMPT + "\n\n"
    for m in history[-MAX_HISTORY:]:
        if m["role"] == "user":
            final += f"User: {m['content']}\n"
        if m["role"] == "assistant":
            final += f"Kachra: {m['content']}\n"
    final += "Kachra: "
    return final


# ------------------------------
# ROOT
# ------------------------------
@app.route("/")
def home():
    return "Kachra AI backend is live!"

# ------------------------------
# CHAT
# ------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_msg = (data.get("message") or "").strip()
        session_id = data.get("session_id") or "default"

        if not HF_TOKEN:
            return jsonify({"reply": "HF token missing!"}), 500

        if not user_msg:
            return jsonify({"reply": "Kuch to bol yaar 😄"}), 400

        # init session
        if session_id not in session_store:
            session_store[session_id] = []

        session_store[session_id].append({"role": "user", "content": user_msg})

        # build final prompt
        prompt = build_prompt(session_store[session_id])

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 180,
                "temperature": 0.7,
                "top_p": 0.9,
                "return_full_text": False
            }
        }

        # retry logic
        reply_text = None
        for retry in [1, 2, 3]:
            try:
                r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=40)

                if r.status_code == 503:
                    time.sleep(2)
                    continue

                if r.status_code != 200:
                    return jsonify({"reply": f"HF error {r.status_code}"}), 500

                out = r.json()

                if isinstance(out, list) and "generated_text" in out[0]:
                    reply_text = out[0]["generated_text"]
                elif "generated_text" in out:
                    reply_text = out["generated_text"]

                break

            except Exception:
                time.sleep(1)
                continue

        if not reply_text:
            reply_text = "Aaj model ka mood off hai 😭"

        reply_text = clean(reply_text)
        reply_text = convert_amazon_links(reply_text)

        session_store[session_id].append({"role": "assistant", "content": reply_text})

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"reply": f"Kachra saved from crash 😅: {e}"}), 200


# ------------------------------
# RESET
# ------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    sid = (request.get_json(force=True) or {}).get("session_id") or "default"
    session_store.pop(sid, None)
    return jsonify({"message": "Chat reset!"}), 200


# ------------------------------
# RUN (LOCAL ONLY)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
