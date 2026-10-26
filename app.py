from flask import Flask, render_template_string, request, Response, session, redirect, url_for
from google import genai
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'college_project_secret_key_123')

client = genai.Client()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFlow AI - Personal Assistant</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Marked.js & Highlight.js -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark-dimmed.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        :root {
            --bg-main: #0b0f17;
            --bg-card: #121824;
            --bg-input: #1b2234;
            --border-subtle: #242f46;
            --accent-primary: #3b82f6;
            --accent-hover: #2563eb;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --user-bubble: #1e293b;
            --ai-bubble: #111827;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }

        .chat-app {
            width: 100%;
            max-width: 900px;
            height: 94vh;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Top Header */
        .chat-header {
            padding: 18px 26px;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(18, 24, 36, 0.85);
            backdrop-filter: blur(10px);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .badge-status {
            width: 9px;
            height: 9px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
        }

        .header-title h1 {
            font-size: 17px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }

        .clear-btn {
            background: transparent;
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .clear-btn:hover {
            color: #ef4444;
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.08);
        }

        /* Chat Conversation Area */
        .chat-body {
            flex: 1;
            padding: 24px 28px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
            scroll-behavior: smooth;
        }

        .chat-body::-webkit-scrollbar {
            width: 6px;
        }
        .chat-body::-webkit-scrollbar-thumb {
            background: var(--border-subtle);
            border-radius: 4px;
        }

        .message-row {
            display: flex;
            width: 100%;
        }

        .message-row.user-row { justify-content: flex-end; }
        .message-row.ai-row { justify-content: flex-start; }

        .message-bubble {
            max-width: 82%;
            padding: 14px 18px;
            border-radius: 14px;
            font-size: 14.5px;
            line-height: 1.6;
            word-wrap: break-word;
        }

        .user-bubble {
            background: var(--user-bubble);
            color: #ffffff;
            border: 1px solid #334155;
            border-bottom-right-radius: 4px;
        }

        .ai-bubble {
            background: var(--ai-bubble);
            color: #cbd5e1;
            border: 1px solid var(--border-subtle);
            border-bottom-left-radius: 4px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            width: 100%;
        }

        .sender-tag {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .user-tag { color: #60a5fa; justify-content: flex-end; }
        .ai-tag { color: #38bdf8; }

        .thinking-indicator {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: var(--text-muted);
            font-size: 13.5px;
            font-style: italic;
        }

        /* Markdown & Code Customization */
        .ai-bubble p { margin-bottom: 10px; }
        .ai-bubble p:last-child { margin-bottom: 0; }
        .ai-bubble ul, .ai-bubble ol { margin: 8px 0 12px 20px; }
        .ai-bubble li { margin-bottom: 4px; }
        
        pre {
            background: #090d16 !important;
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 14px;
            margin: 12px 0;
            overflow-x: auto;
        }

        code {
            font-family: 'Fira Code', monospace;
            font-size: 13px;
        }

        p code {
            background: #1e2638;
            color: #38bdf8;
            padding: 2px 6px;
            border-radius: 5px;
            font-size: 13px;
        }

        /* Footer / Input Area */
        .chat-footer {
            padding: 16px 24px 20px;
            border-top: 1px solid var(--border-subtle);
            background: var(--bg-card);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .quick-chips {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .chip-btn {
            background: var(--bg-input);
            color: var(--text-muted);
            border: 1px solid var(--border-subtle);
            padding: 6px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12.5px;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .chip-btn:hover {
            color: var(--text-main);
            border-color: var(--accent-primary);
            background: rgba(59, 130, 246, 0.12);
        }

        .input-bar {
            display: flex;
            align-items: flex-end;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 8px 12px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .input-bar:focus-within {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: inherit;
            font-size: 14px;
            resize: none;
            height: 24px;
            max-height: 120px;
            outline: none;
            padding: 4px 6px;
            line-height: 20px;
        }

        textarea::placeholder { color: #64748b; }

        .send-btn {
            background: var(--accent-primary);
            color: #ffffff;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            transition: background 0.2s ease, transform 0.1s ease;
            flex-shrink: 0;
        }

        .send-btn:hover { background: var(--accent-hover); }
        .send-btn:active { transform: scale(0.95); }
        .send-btn:disabled { background: #334155; cursor: not-allowed; opacity: 0.6; }
        .send-btn svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 2.2; }
    </style>
</head>
<body>

    <div class="chat-app">
        <!-- Top App Bar -->
        <header class="chat-header">
            <div class="header-title">
                <span class="badge-status"></span>
                <h1>DevFlow Assistant</h1>
            </div>
            <form action="/clear" method="POST" style="margin: 0;">
                <button type="submit" class="clear-btn">Clear Session</button>
            </form>
        </header>

        <!-- Dynamic Chat Conversation -->
        <div class="chat-body" id="chat-body">
            {% if not history %}
                <div class="message-row ai-row">
                    <div class="message-bubble ai-bubble">
                        <div class="sender-tag ai-tag">Assistant</div>
                        <p>Welcome! I'm your context-aware virtual assistant. Ask me to design architecture, debug code, or solve algorithmic problems.</p>
                    </div>
                </div>
            {% endif %}

            {% for message in history %}
                {% if message.role == 'user' %}
                    <div class="message-row user-row">
                        <div class="message-bubble user-bubble">
                            <div class="sender-tag user-tag">You</div>
                            <div>{{ message.text }}</div>
                        </div>
                    </div>
                {% else %}
                    <div class="message-row ai-row">
                        <div class="message-bubble ai-bubble">
                            <div class="sender-tag ai-tag">Assistant</div>
                            <div class="rendered-content">{{ message.text }}</div>
                        </div>
                    </div>
                {% endif %}
            {% endfor %}
        </div>

        <!-- Interactive Footer -->
        <footer class="chat-footer">
            <div class="quick-chips">
                <button type="button" class="chip-btn" onclick="setPrompt('Write a Java method for binary search')">☕ Java Binary Search</button>
                <button type="button" class="chip-btn" onclick="setPrompt('Design an LRU Cache with O(1) operations')">⚡ LRU Cache Design</button>
                <button type="button" class="chip-btn" onclick="setPrompt('Explain microservices vs monolithic architecture in 2 lines')">🏢 System Architecture</button>
            </div>

            <form id="chat-form" class="input-bar">
                <textarea id="prompt" name="prompt" rows="1" placeholder="Type your query or instruction..."></textarea>
                <button type="submit" id="send-btn" class="send-btn" aria-label="Send">
                    <svg viewBox="0 0 24 24">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </form>
        </footer>
    </div>

    <script>
        const chatBody = document.getElementById('chat-body');
        const promptInput = document.getElementById('prompt');
        const form = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');

        chatBody.scrollTop = chatBody.scrollHeight;

        // Auto-render any existing markdown messages
        document.querySelectorAll('.rendered-content').forEach((el) => {
            el.innerHTML = marked.parse(el.textContent);
            el.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
        });

        // Quick prompt setter
        function setPrompt(text) {
            promptInput.value = text;
            promptInput.focus();
            autoResizeTextarea();
        }

        // Auto resize textarea height
        promptInput.addEventListener('input', autoResizeTextarea);
        function autoResizeTextarea() {
            promptInput.style.height = 'auto';
            promptInput.style.height = (promptInput.scrollHeight < 120 ? promptInput.scrollHeight : 120) + 'px';
        }

        // Handle Enter key for submit (Shift+Enter for new line)
        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = promptInput.value.trim();
            if (!promptText) return;

            // 1. Add User Bubble
            const userRow = document.createElement('div');
            userRow.className = 'message-row user-row';
            userRow.innerHTML = `
                <div class="message-bubble user-bubble">
                    <div class="sender-tag user-tag">You</div>
                    <div>${escapeHtml(promptText)}</div>
                </div>
            `;
            chatBody.appendChild(userRow);

            promptInput.value = '';
            promptInput.style.height = '24px';
            chatBody.scrollTop = chatBody.scrollHeight;

            // 2. Add AI Placeholder Bubble
            const aiRow = document.createElement('div');
            aiRow.className = 'message-row ai-row';
            aiRow.innerHTML = `
                <div class="message-bubble ai-bubble">
                    <div class="sender-tag ai-tag">Assistant</div>
                    <div class="ai-stream-content"><span class="thinking-indicator">Assistant is thinking...</span></div>
                </div>
            `;
            chatBody.appendChild(aiRow);
            chatBody.scrollTop = chatBody.scrollHeight;

            const streamContent = aiRow.querySelector('.ai-stream-content');
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

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    
                    streamContent.innerHTML = marked.parse(fullResponse);
                    streamContent.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
                    chatBody.scrollTop = chatBody.scrollHeight;
                }

                // Decoupled session persistence
                await fetch('/save_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_prompt: promptText, ai_response: fullResponse })
                });

            } catch (err) {
                streamContent.innerHTML = `<span style="color:#ef4444;">Error connecting to the service. Please retry.</span>`;
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
    user_prompt = request.form.get("prompt", "")
    
    if 'history' not in session:
        session['history'] = []

    gemini_contents = []
    for h in session['history']:
        role = "user" if h['role'] == 'user' else "model"
        gemini_contents.append({"role": role, "parts": [{"text": h['text']}]})
    
    gemini_contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    def generate_stream():
        try:
            response = client.models.generate_content_stream(
                model="gemini-3.8-flash",
                contents=gemini_contents,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "unavailable" in error_str.lower() or "ResourceExhausted" in error_str:
                yield "AI server is experiencing high traffic. Please retry in a moment."
            else:
                yield f"Error: {e}"

    return Response(generate_stream(), mimetype='text/plain')

@app.route("/save_message", methods=["POST"])
def save_message():
    data = request.get_json() or {}
    user_prompt = data.get("user_prompt", "")
    ai_response = data.get("ai_response", "")

    if 'history' not in session:
        session['history'] = []

    if user_prompt and ai_response:
        history = list(session['history'])
        history.append({'role': 'user', 'text': user_prompt})
        history.append({'role': 'ai', 'text': ai_response})
        session['history'] = history
        session.modified = True

    return {"status": "ok"}

@app.route("/clear", methods=["POST"])
def clear():
    session.pop('history', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)