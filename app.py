from flask import Flask, render_template_string, request, Response
from google import genai
import os

app = Flask(__name__)

# Initialize the Gemini client
client = genai.Client()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Chat Assistant - Streaming</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        textarea { width: 100%; height: 100px; padding: 10px; margin-bottom: 10px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .response { background: #f4f4f4; padding: 15px; margin-top: 20px; border-left: 4px solid #007bff; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h2>Gemini Flask Chat App (Streaming)</h2>
    <form id="chat-form">
        <textarea id="prompt" name="prompt" placeholder="Ask something..."></textarea><br>
        <button type="submit">Send to AI</button>
    </form>
    <div class="response" id="response-box"><strong>AI Response:</strong><p id="output"></p></div>

    <script>
        const form = document.getElementById('chat-form');
        const output = document.getElementById('output');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('prompt').value;
            output.textContent = "Thinking...";

            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'prompt=' + encodeURIComponent(promptText)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            output.textContent = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                output.textContent += decoder.decode(value, { stream: true });
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/generate", methods=["POST"])
def generate():
    user_prompt = request.form.get("prompt")
    def generate_stream():
        try:
            response = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=user_prompt,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Error: {e}"

    return Response(generate_stream(), mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True)