from flask import Flask, render_template_string, request, Response, session, redirect, url_for
from google import genai
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'college_project_secret_key')

# Initialize the Gemini client
client = genai.Client()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Chat Assistant - Pro Memory Edition</title>
    
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
            max-width: 800px;
            height: 92vh;
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
            padding: 18px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-header h2 { font-size: 18px; font-weight: 600; }
        .clear-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            padding: 6px 14px;
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
        .user-message {
            background: #007bff;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 2px;
        }
        .ai-message {
            background: #ffffff;
            color: #333;
            align-self: flex-start;
            border-left: 4px solid #007bff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-bottom-left-radius: 2px;
            width: 85%;
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
            <h2>⚡ AI Chat Assistant (Memory Pro)</h2>
            <form action="/clear" method="POST" style="margin:0;">
                <button type="submit" class="clear-btn">Clear Chat</button>
            </form>
        </div>

        <div class="chat-body" id="chat-body">
            {% if not history %}
                <div class="message ai-message">
                    <strong>AI Assistant:</strong><br>
                    Namaste! Main aapka AI assistant hoon. Aap mujhse koi bhi sawal pooch sakte hain aur main purani baatein bhi yaad rakhunga!
                </div>
            {% endif %}
            
            {% for message in history %}
                {% if message.role == 'user' %}
                    <div class="message user-message"><strong>You:</strong><br>{{ message.text }}</div>
                {% else %}
                    <div class="message ai-message"><strong>AI:</strong><br>{{ message.text|safe }}</div>
                {% endif %}
            {% endfor %}
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
        const chatBody = document.getElementById('chat-body');
        chatBody.scrollTop = chatBody.scrollHeight;

        function setPrompt(text) {
            document.getElementById('prompt').value = text;
        }

        const form = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptInput = document.getElementById('prompt');
            const promptText = promptInput.value;
            if (!promptText.trim()) return;

            // 1. Append User Message to UI
            const userMsgDiv = document.createElement('div');
            userMsgDiv.className = 'message user-message';
            userMsgDiv.innerHTML = `<strong>You:</strong><br>${escapeHtml(promptText)}`;
            chatBody.appendChild(userMsgDiv);

            promptInput.value = '';
            chatBody.scrollTop = chatBody.scrollHeight;

            // 2. Append AI Thinking Bubble
            const aiMsgDiv = document.createElement('div');
            aiMsgDiv.className = 'message ai-message';
            aiMsgDiv.innerHTML = `<strong>AI:</strong><br><span class="thinking">AI is thinking...</span>`;
            chatBody.appendChild(aiMsgDiv);
            chatBody.scrollTop = chatBody.scrollHeight;

            sendBtn.disabled = true;

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'prompt=' + encodeURIComponent(promptText)
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                let fullResponse = "";
                const aiContentDiv = aiMsgDiv.querySelector('div') || aiMsgDiv;

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    
                    aiMsgDiv.innerHTML = `<strong>AI:</strong><br>` + marked.parse(fullResponse);
                    
                    document.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                    chatBody.scrollTop = chatBody.scrollHeight;
                }
            } catch (err) {
                aiMsgDiv.innerHTML = `<strong>AI:</strong><br><span style="color:red;">Error connecting to server.</span>`;
            } finally {
                sendBtn.disabled = false;
            }
        });

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    if 'history' not in session:
        session['history'] = []
    return render_template_string(HTML_TEMPLATE, history=session['history'])

@app.route("/generate", methods=["POST"])
def generate():
    user_prompt = request.form.get("prompt")
    
    if 'history' not in session:
        session['history'] = []

    # Convert session history into Gemini format expected contents list
    gemini_contents = []
    for h in session['history']:
        role = "user" if h['role'] == 'user' else "model"
        gemini_contents.append({"role": role, "parts": [{"text": h['text']}]})
    
    # Add current prompt
    gemini_contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    def generate_stream():
        full_ai_response = ""
        try:
            response = client.models.generate_content_stream(
                model="gemini-3.8-flash",
                contents=gemini_contents,
            )
            for chunk in response:
                if chunk.text:
                    full_ai_response += chunk.text
                    yield chunk.text
            
            # Save to session history after complete generation
            history = session.get('history', [])
            history.append({'role': 'user', 'text': user_prompt})
            # Store parsed markdown HTML or plain text for rendering
            history.append({'role': 'ai', 'text': full_ai_response})
            session['history'] = history
            session.modified = True

        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "unavailable" in error_str.lower() or "ResourceExhausted" in error_str:
                err_msg = "AI server par abhi high demand hai. Kripya refresh karke try karein!"
            else:
                err_msg = f"Error: {e}"
            yield err_msg

    return Response(generate_stream(), mimetype='text/plain')

@app.route("/clear", methods=["POST"])
def clear():
    session.pop('history', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)