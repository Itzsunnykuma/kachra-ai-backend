import gradio as gr
import requests
import os

HF_TOKEN = os.getenv("HF_TOKEN")  # stored securely in Render
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def chat_with_llama(message, history):
    conversation = ""
    for human, bot in history:
        conversation += f"Human: {human}\nAssistant: {bot}\n"
    conversation += f"Human: {message}\nAssistant:"
    
    payload = {"inputs": conversation, "parameters": {"max_new_tokens": 256}}
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        return "Error: " + response.text

    text = response.json()[0]["generated_text"].split("Assistant:")[-1].strip()
    return text

chatbot = gr.ChatInterface(
    fn=chat_with_llama,
    title="🤖 Kachra AI",
    description="Fun AI powered by Meta-Llama 3",
)

if __name__ == "__main__":
    chatbot.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))
