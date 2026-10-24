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
    
    <!-- Marked.js for Markdown Parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- Highlight.js for Beautiful Code Syntax Highlighting (Dark Theme) -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        body { font-family: Arial, sans-serif; max-width: 650px; margin: 40px auto; padding: 20px; background: #fdfdfd; }
        textarea { width: 100%; height: 90px; padding: 10px; margin-bottom: 5px; border-radius: 4px; border: 1px solid #ccc; font-family: inherit; }
        .btn-group { display: flex; gap: 10px; margin-bottom: 10px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        button.clear-btn { background: #6c757d; }
        button:hover { opacity: 0.9; }
        
        .response { background: #ffffff; padding: 20px; margin-top: 20px; border-left: 4px solid #007bff; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); line-height: 1.6; }
        
        /* Quick Prompt Buttons Style */
        .quick-prompts { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
        .quick-btn { background: #e9ecef; color: #333; border: 1px solid #ced4da; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: normal; }
        .quick-btn:hover { background: #dde2e6; }
        
        /* Typing Indicator Effect */
        .thinking { color: #888; font-style: italic; }

        /* Code block styling adjustments */
        pre { background: #282c34; padding: 15px; border-radius: 6px; overflow-x: auto; }
        code { font-family: 'Courier New', Courier, monospace; }
        p code { background: #f1f3f5; padding: 2px 6px; border-radius: 4px; color: #d63384; }
    </style>
</head>
<body>
    <h2>Gemini Flask Chat App (Pro Edition)</h2>
    <form id="chat-form">
        <textarea id="prompt" name="prompt" placeholder="Ask something or write code..."></textarea>
        
        <!-- Quick-Prompt Buttons -->
        <div class="quick-prompts">
            <button type="button" class="quick-btn" onclick="setPrompt('Write a Java method for binary search')">☕ Java Binary Search</button>
            <button type="button" class="quick-btn" onclick="setPrompt('Explain Python in 1 line')">🐍 Python in 1 line</button>
            <button type="button" class="quick-btn" onclick="setPrompt('Tell me a funny coding joke')">😄 Coding Joke</button>
        </div>

        <div class="btn-group">
            <button type="submit" id="send-btn">Send to AI</button>
            <button type="button" class="clear-btn" onclick="clearChat()">Clear Chat</button>
        </div>
    </form>
    
    <div class="response" id="response-box">
        <strong>AI Response:</strong>
        <div id="output" style="margin-top: 10px;"></div>
    </div>

    <script>
        // Function to fill prompt text automatically
        function setPrompt(text) {
            document.getElementById('prompt').value = text;
        }

        // Function to clear chat box and input
        function clearChat() {
            document.getElementById('prompt').value = '';
            document.getElementById('output').innerHTML = '';
        }

        const form = document.getElementById('chat-form');
        const output = document.getElementById('output');
        const sendBtn = document.getElementById('send-btn');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('prompt').value;
            if (!promptText.trim()) return;

            // Show Typing Indicator
            output.className = "thinking";
            output.textContent = "AI is thinking...";
            sendBtn.disabled = true;

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'prompt=' + encodeURIComponent(promptText)
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                output.className = "";
                let fullResponse = "";

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    
                    // Live Markdown Rendering as it streams
                    output.innerHTML = marked.parse(fullResponse);
                    
                    // Apply Code Highlighting to code blocks
                    document.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                }
            } catch (err) {
                output.className = "";
                output.textContent = "Error connecting to server.";
            } finally {
                sendBtn.disabled = false;
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
                model="gemini-3.8-flash",
                contents=user_prompt,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e: