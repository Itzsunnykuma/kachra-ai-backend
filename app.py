HF_API_URL = "https://router.huggingface.co/models/meta-llama/meta-llama-3-8b-instruct"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"response": "Please provide a message."})

        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt}

        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()

        # HF Router always returns list of dicts
        if isinstance(result, list) and "generated_text" in result[0]:
            text = result[0]["generated_text"]
        else:
            text = str(result)

        return jsonify({"response": text})

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "Error connecting to AI."})
