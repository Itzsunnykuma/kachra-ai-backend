import gradio as gr
from huggingface_hub import InferenceClient

client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")

def chat_with_ai(message, history):
    response = client.text_generation(
        message,
        max_new_tokens=200,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
    )
    return response

app = gr.ChatInterface(  # 👈 renamed demo → app
    fn=chat_with_ai,
    title="Kachra AI 🤖",
    description="Fun public AI chatbot — talks trash like your best friend 😄",
)

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=10000)
