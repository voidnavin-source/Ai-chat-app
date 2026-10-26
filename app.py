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
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Marked.js & Highlight.js -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        :root {
            --bg-page: #0d1117;
            --bg-input-container: #161b22;
            --border-line: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent-blue: #2f81f7;
            --user-bubble-bg: #1f2937;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-page);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Top Sticky Header */
        header {
            width: 100%;
            height: 56px;
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(13, 17, 23, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border-line);
            z-index: 10;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            font-weight: 600;
            letter-spacing: -0.2px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #238636;
            border-radius: 50%;
            box-shadow: 0 0 8px #238636;
        }

        .clear-btn {
            background: transparent;
            border: 1px solid var(--border-line);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .clear-btn:hover {
            color: #f85149;
            border-color: #f85149;
            background: rgba(248, 81, 73, 0.1);
        }

        /* Full Screen Scrollable Chat Container */
        .chat-scroll-area {
            flex: 1;
            overflow-y: auto;
            scroll-behavior: smooth;
            padding: 30px 16px 140px 16px;
        }

        .chat-scroll-area::-webkit-scrollbar {
            width: 8px;
        }
        .chat-scroll-area::-webkit-scrollbar-thumb {
            background: #21262d;
            border-radius: 4px;
        }

        .conversation-wrapper {
            max-width: 768px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 28px;
        }

        .message-block {
            display: flex;
            flex-direction: column;
            width: 100%;
        }

        .message-header {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .user-block .message-header { color: #58a6ff; justify-content: flex-end; }
        .ai-block .message-header { color: #7ee787; }

        .bubble-content {
            font-size: 15px;
            line-height: 1.65;
            word-wrap: break-word;
        }

        .user-block {
            align-items: flex-end;
        }

        .user-block .bubble-content {
            background: var(--user-bubble-bg);
            padding: 12px 18px;
            border-radius: 18px 18px 4px 18px;
            max-width: 85%;
            border: 1px solid #374151;
            color: #ffffff;
        }

        .ai-block {
            align-items: flex-start;
        }

        .ai-block .bubble-content {
            width: 100%;
            color: #c9d1d9;
        }

        /* Markdown and Pre formatting */
        .ai-block p { margin-bottom: 12px; }
        .ai-block p:last-child { margin-bottom: 0; }
        .ai-block ul, .ai-block ol { margin: 8px 0 14px 24px; }
        .ai-block li { margin-bottom: 6px; }

        pre {
            background: #161b22 !important;
            border: 1px solid var(--border-line);
            border-radius: 8px;
            padding: 16px;
            margin: 14px 0;
            overflow-x: auto;
        }

        code {
            font-family: 'Fira Code', monospace;
            font-size: 13.5px;
        }

        p code {
            background: #21262d;
            color: #79c0ff;
            padding: 3px 6px;
            border-radius: 4px;
        }

        .thinking-indicator {
            color: var(--text-secondary);
            font-style: italic;
        }

        /* Bottom Floating Input Bar */
        .input-dock {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: linear-gradient(180deg, rgba(13, 17, 23, 0) 0%, rgba(13, 17, 23, 0.9) 25%, #0d1117 100%);
            padding: 0 16px 20px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            z-index: 20;
        }

        .dock-container {
            width: 100%;
            max-width: 768px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .quick-chips {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            white-space: nowrap;
            padding-bottom: 4px;
        }

        .chip {
            background: rgba(22, 27, 34, 0.8);
            border: 1px solid var(--border-line);
            color: var(--text-secondary);
            padding: 5px 12px;
            border-radius: 16px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .chip:hover {
            color: var(--text-primary);
            border-color: var(--accent-blue);
            background: #161b22;
        }

        .input-box {
            background: var(--bg-input-container);
            border: 1px solid var(--border-line);
            border-radius: 14px;
            display: flex;
            align-items: flex-end;
            padding: 10px 14px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .input-box:focus-within {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 2px rgba(47, 129, 247, 0.25);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 14.5px;
            line-height: 22px;
            max-height: 140px;
            height: 24px;
            resize: none;
            outline: none;
            padding: 2px 8px 2px 0;
        }

        textarea::placeholder { color: #6e7681; }

        .send-btn {
            background: var(--accent-blue);
            border: none;
            color: white;
            width: 34px;
            height: 34px;
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            transition: opacity 0.2s ease;
            flex-shrink: 0;
        }

        .send-btn:disabled {
            background: #21262d;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .send-btn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2.2; }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span class="status-dot"></span>
            <span>DevFlow AI</span>
        </div>
        <form action="/clear" method="POST" style="margin: 0;">
            <button type="submit" class="clear-btn">Clear Chat</button>
        </form>
    </header>

    <div class="chat-scroll-area" id="scroll-area">
        <div class="conversation-wrapper" id="conversation-container">
            {% if not history %}
                <div class="message-block ai-block">
                    <div class="message-header">DevFlow AI</div>
                    <div class="bubble-content">
                        <p>Namaste! Main aapka AI personal assistant hoon. Coding, architecture design, ya koi bhi complex sawal poocho — baatcheet full screen par smoothly scroll hogi.</p>
                    </div>
                </div>
            {% endif %}

            {% for message in history %}
                {% if message.role == 'user' %}
                    <div class="message-block user-block">
                        <div class="message-header">You</div>
                        <div class="bubble-content">{{ message.text }}</div>
                    </div>
                {% else %}
                    <div class="message-block ai-block">
                        <div class="message-header">DevFlow AI</div>
                        <div class="bubble-content rendered-content">{{ message.text }}</div>
                    </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <div class="input-dock">
        <div class="dock-container">
            <div class="quick-chips">
                <button type="button" class="chip" onclick="setPrompt('Write a clean Java solution for LRU Cache with O(1) time complexity')">☕ LRU Cache (Java)</button>
                <button type="button" class="chip" onclick="setPrompt('Design a high-scale real-time notification engine with Kafka and Redis')">⚡ Notification Architecture</button>
                <button type="button" class="chip" onclick="setPrompt('Explain difference between TCP and UDP with simple analogies')">🌐 TCP vs UDP</button>
            </div>

            <form id="chat-form" class="input-box">
                <textarea id="prompt" name="prompt" rows="1" placeholder="Message DevFlow AI..."></textarea>
                <button type="submit" id="send-btn" class="send-btn" aria-label="Send">
                    <svg viewBox="0 0 24 24">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </form>
        </div>
    </div>

    <script>
        const scrollArea = document.getElementById('scroll-area');
        const container = document.getElementById('conversation-container');
        const promptInput = document.getElementById('prompt');
        const form = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');

        function scrollToBottom() {
            scrollArea.scrollTop = scrollArea.scrollHeight;
        }
        scrollToBottom();

        // Render previous markdown history
        document.querySelectorAll('.rendered-content').forEach((el) => {
            el.innerHTML = marked.parse(el.textContent);
            el.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
        });

        function setPrompt(text) {
            promptInput.value = text;
            promptInput.focus();
            autoResize();
        }

        promptInput.addEventListener('input', autoResize);
        function autoResize() {
            promptInput.style.height = 'auto';
            promptInput.style.height = Math.min(promptInput.scrollHeight, 140) + 'px';
        }

        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = promptInput.value.trim();
            if (!text) return;

            // 1. Append User Message
            const userBlock = document.createElement('div');
            userBlock.className = 'message-block user-block';
            userBlock.innerHTML = `
                <div class="message-header">You</div>
                <div class="bubble-content">${escapeHtml(text)}</div>
            `;
            container.appendChild(userBlock);

            promptInput.value = '';
            promptInput.style.height = '24px';
            scrollToBottom();

            // 2. Append AI Streaming Placeholder
            const aiBlock = document.createElement('div');
            aiBlock.className = 'message-block ai-block';
            aiBlock.innerHTML = `
                <div class="message-header">DevFlow AI</div>
                <div class="bubble-content ai-stream"><span class="thinking-indicator">DevFlow is thinking...</span></div>
            `;
            container.appendChild(aiBlock);
            scrollToBottom();

            const streamBox = aiBlock.querySelector('.ai-stream');
            sendBtn.disabled = true;

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'prompt=' + encodeURIComponent(text)
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullResponse = "";

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    
                    streamBox.innerHTML = marked.parse(fullResponse);
                    streamBox.querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
                    scrollToBottom();
                }

                // Background session persistence
                await fetch('/save_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_prompt: text, ai_response: fullResponse })
                });

            } catch (err) {
                streamBox.innerHTML = `<span style="color:#f85149;">Connection error. Please try again.</span>`;
            } finally {
                sendBtn.disabled = false;
            }
        });

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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
                yield "Server under high load. Please retry in a few seconds."
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