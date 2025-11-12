import gradio as gr
from huggingface_hub import InferenceClient

# Initialize Hugging Face client (replace with your model if different)
client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")

# Define your chatbot logic
def chat_with_ai(message, history):
    response = client.text_generation(
        message,
        max_new_tokens=200,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
    )
    return response

# Create the Gradio demo
demo = gr.ChatInterface(
    fn=chat_with_ai,
    title="Kachra AI 🤖",
    description="Fun public AI chatbot — talks trash like your best friend 😄",
)

# Run when started by Render
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=10000)
