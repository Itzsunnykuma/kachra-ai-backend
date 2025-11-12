import gradio as gr
from huggingface_hub import InferenceClient

# Initialize the Hugging Face model client
client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")

# Define chatbot function
def chat_with_ai(message, history):
    response = client.text_generation(
        message,
        max_new_tokens=200,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
    )
    return response

# Create the Gradio app (must be named 'app' for Gunicorn)
app = gr.ChatInterface(
    fn=chat_with_ai,
    title="Kachra AI 🤖",
    description="Public fun chatbot — talk to Kachra AI like your funny friend 😄",
)

# Run app locally (Render ignores this line — it uses gunicorn app:app)
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=10000)
