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
    <title>AI Chat Assistant - Pro Edition</title>
    
    <!-- Marked.js for Markdown Parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- Highlight.js for Beautiful Code Syntax Highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .chat-container {
            width: 100%;
            max-width: 750px;
            height: 90vh;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-header {
            background: #007bff;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-header h2 { font-size: 20px; font-weight: 600; }
        .clear-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }
        .clear-btn:hover { background: rgba(255, 255, 255, 0.3); }

        .chat-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 14px;
            word-wrap: break-word;
        }
        .ai-message {
            background: #ffffff;
            align-self: flex-start;
            border-left: 4px solid #007bff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            width: 100%;
        }
        .thinking { color: #888; font-style: italic; }

        .chat-footer {
            padding: 15px 20px;
            background: #ffffff;
            border-top: 1px solid #e9ecef;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .quick-prompts {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .quick-btn {
            background: #e9ecef;
            color: #495057;
            border: none;
            padding: 6px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .quick-btn:hover { background: #007bff; color: white; }

        .input-box {
            display: flex;
            gap: 10px;
        }
        textarea {
            flex: 1;
            height: 45px;
            max-height: 100px;
            padding: 10px 15px;
            border: 1px solid #ced4da;
            border-radius: 8px;
            resize: none;
            font-family: inherit;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        textarea:focus { border-color: #007bff; }
        
        button[type="submit"] {
            background: #007bff;
            color: white;
            border: none;
            padding: 0 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }
        button[type="submit"]:hover { background: #0056b3; }
        button:disabled { background: #b0c4de; cursor: not-allowed; }

        pre { background: #282c34; padding: 12px; border-radius: 6px; overflow-x: auto; margin-top: 8px; }
        code { font-family: 'Courier New', Courier, monospace; color: #abb2bf; }
        p code { background: #e2e8f0; padding: 2px 5px; border-radius: 4px; color: #d63384; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>⚡ AI Chat Assistant (Pro)</h2>
            <button class="clear-btn" onclick="clearChat()">Clear Chat</button>
        </div>

        <div class="chat-body" id="chat-body">
            <div class="message ai-message">
                <strong>AI Assistant:</strong><br>
                <div id="output" style="margin-top: 5px;">Namaste! Main aapka AI assistant hoon. Neeche diye gaye quick prompts par click karein ya apna sawal puchein.</div>
            </div>
        </div>

        <div class="chat-footer">
            <div class="quick-prompts">
                <button type="button" class="quick-btn" onclick="setPrompt('Write a Java method for binary search')">☕ Java Binary Search</button>
                <button type="button" class="quick-btn" onclick="setPrompt('Explain Python in 1 line')">🐍 Python in 1 line</button>
                <button type="button" class="quick-btn" onclick="setPrompt('Tell me a funny coding joke')">😄 Coding Joke</button>
            </div>

            <form id="chat-form" class="input-box">
                <textarea id="prompt" name="prompt" placeholder="Ask something or write code..."></textarea>
                <button type="submit" id="send-btn">Send</button>
            </form>
        </div>
    </div>

    <script>
        function setPrompt(text) {
            document.getElementById('prompt').value = text;
        }

        function clearChat() {
            document.getElementById('output').innerHTML = "Chat cleared. Aap naya sawal pooch sakte hain!";
            document.getElementById('prompt').value = '';
        }

        const form = document.getElementById('chat-form');
        const output = document.getElementById('output');
        const sendBtn = document.getElementById('send-btn');
        const chatBody = document.getElementById('chat-body');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('prompt').value;
            if (!promptText.trim()) return;

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
                    
                    output.innerHTML = marked.parse(fullResponse);
                    
                    document.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                    chatBody.scrollTop = chatBody.scrollHeight;
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
            error_str = str(e)
            if "503" in error_str or "unavailable" in error_str.lower() or "ResourceExhausted" in error_str:
                yield "AI server par abhi high demand hai. Kripya ek baar refresh karke dobara try karein!"
            else:
                yield f"Error: {e}"

    return Response(generate_stream(), mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True)