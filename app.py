from flask import Flask, render_template_string, request, Response, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'devflow_ultra_secure_key_2026')

client = genai.Client()
DB_FILE = "assistant.db"

# ----------------- DATABASE SETUP ----------------- #
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            remind_time TEXT NOT NULL,
            is_dismissed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- HTML TEMPLATES ----------------- #
AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFlow AI - Workspace</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: #090d16;
            color: #f1f5f9;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .auth-container {
            width: 100%;
            max-width: 380px;
            padding: 36px 30px;
            background: #111726;
            border: 1px solid #1e293b;
            border-radius: 18px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6);
        }
        .auth-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 20px;
            font-weight: 700;
            color: #38bdf8;
            margin-bottom: 6px;
        }
        .auth-sub {
            text-align: center;
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 24px;
        }
        .input-group { margin-bottom: 16px; }
        label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        input {
            width: 100%;
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 11px 14px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus { border-color: #38bdf8; }
        button {
            width: 100%;
            background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
            color: #fff;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            margin-top: 10px;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.92; }
        .switch-link {
            text-align: center;
            margin-top: 20px;
            font-size: 13px;
            color: #94a3b8;
        }
        .switch-link a { color: #38bdf8; text-decoration: none; font-weight: 600; }
        .error-msg {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 9px 12px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 16px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="auth-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
            DevFlow AI
        </div>
        <p class="auth-sub">{{ mode_title }}</p>

        {% if error %}
            <div class="error-msg">{{ error }}</div>
        {% endif %}

        <form method="POST">
            <div class="input-group">
                <label>Username</label>
                <input type="text" name="username" required autocomplete="off">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">{{ btn_text }}</button>
        </form>

        <div class="switch-link">
            {% if is_login %}
                New developer? <a href="/register">Sign Up</a>
            {% else %}
                Already have account? <a href="/login">Sign In</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

APP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFlow AI Workspace</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/tokyo-night-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        :root {
            --bg-base: #080b11;
            --bg-surface: #0f1420;
            --bg-glass: rgba(15, 20, 32, 0.85);
            --border: #1e2638;
            --border-hover: #334155;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --user-bg: #1a2234;
            --alarm-red: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Top Bar */
        header {
            height: 56px;
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-glass);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            z-index: 20;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.3px;
        }

        .brand-logo svg { color: var(--accent); }

        .persona-badge {
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 8px;
            padding: 2px 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .persona-select {
            background: transparent;
            border: none;
            color: var(--accent);
            font-size: 12px;
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        .persona-select option {
            background: var(--bg-surface);
            color: var(--text-main);
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .user-tag {
            font-size: 13px;
            color: var(--text-sub);
            margin-right: 6px;
        }
        .user-tag span { color: #fff; font-weight: 600; }

        .btn-action {
            background: #151c2c;
            border: 1px solid var(--border);
            color: var(--text-sub);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .btn-action:hover {
            color: var(--text-main);
            border-color: var(--border-hover);
            background: #1e2638;
        }

        .btn-danger:hover {
            color: var(--alarm-red);
            border-color: rgba(239, 68, 68, 0.4);
            background: rgba(239, 68, 68, 0.1);
        }

        /* Workspace Grid */
        .workspace {
            display: flex;
            flex: 1;
            height: calc(100vh - 56px);
            overflow: hidden;
        }

        /* Sidebar */
        aside {
            width: 280px;
            background: var(--bg-surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 16px;
            gap: 16px;
        }

        .sidebar-header {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--text-sub);
            display: flex;
            justify-content: space-between;
        }

        .alarm-form {
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: #151c2c;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
        }

        .alarm-form input {
            background: #0a0e17;
            border: 1px solid var(--border);
            color: #fff;
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 12.5px;
            outline: none;
        }
        .alarm-form input:focus { border-color: var(--accent); }

        .btn-add-alarm {
            background: #0284c7;
            color: #fff;
            border: none;
            padding: 7px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn-add-alarm:hover { opacity: 0.9; }

        .reminders-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .reminder-card {
            background: #151c2c;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .reminder-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .reminder-title { font-size: 13px; font-weight: 600; color: #e2e8f0; }
        .reminder-clock { font-size: 11.5px; color: var(--accent); font-family: 'JetBrains Mono', monospace; }

        .reminder-del {
            background: transparent;
            border: none;
            color: var(--text-sub);
            cursor: pointer;
            font-size: 14px;
        }
        .reminder-del:hover { color: var(--alarm-red); }

        /* Main Scroll Area */
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
            background: var(--bg-base);
        }

        .chat-scroll {
            flex: 1;
            overflow-y: auto;
            scroll-behavior: smooth;
            padding: 30px 24px 150px 24px;
        }

        .chat-scroll::-webkit-scrollbar { width: 6px; }
        .chat-scroll::-webkit-scrollbar-thumb { background: #1e2638; border-radius: 3px; }

        .feed-container {
            max-width: 820px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 28px;
        }

        .msg-row {
            display: flex;
            flex-direction: column;
            width: 100%;
        }

        .msg-role {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .msg-user .msg-role { color: #60a5fa; justify-content: flex-end; }
        .msg-ai .msg-role { color: var(--accent); }

        .msg-user { align-items: flex-end; }
        .msg-user .msg-bubble {
            background: var(--user-bg);
            border: 1px solid #2a374f;
            border-radius: 16px 16px 4px 16px;
            padding: 12px 18px;
            max-width: 82%;
            font-size: 14.5px;
            line-height: 1.6;
            color: #ffffff;
        }

        .msg-ai { align-items: flex-start; }
        .msg-ai .msg-bubble {
            width: 100%;
            font-size: 15px;
            line-height: 1.68;
            color: #cbd5e1;
        }

        /* Code Blocks & Copy Bar */
        .code-container {
            position: relative;
            margin: 14px 0;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid var(--border);
        }

        .code-header {
            background: #111726;
            padding: 6px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--text-sub);
            border-bottom: 1px solid var(--border);
        }

        .copy-code-btn {
            background: transparent;
            border: none;
            color: var(--text-sub);
            cursor: pointer;
            font-size: 11.5px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .copy-code-btn:hover { color: #fff; }

        pre {
            background: #0b0f19 !important;
            padding: 14px 16px;
            overflow-x: auto;
            margin: 0 !important;
        }

        code { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; }
        p code { background: #161e30; color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 13px; }

        /* Floating Input Bar */
        .dock-bar {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background: linear-gradient(180deg, rgba(8, 11, 17, 0) 0%, rgba(8, 11, 17, 0.96) 25%, #080b11 100%);
            padding: 0 20px 22px 20px;
            display: flex;
            justify-content: center;
            z-index: 15;
        }

        .dock-content {
            width: 100%;
            max-width: 820px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .chips-row {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            white-space: nowrap;
            scrollbar-width: none;
        }
        .chips-row::-webkit-scrollbar { display: none; }

        .prompt-chip {
            background: rgba(17, 23, 38, 0.7);
            border: 1px solid var(--border);
            color: var(--text-sub);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .prompt-chip:hover { color: #fff; border-color: var(--accent); background: #151c2c; }

        .input-pill {
            background: #111726;
            border: 1px solid var(--border);
            border-radius: 14px;
            display: flex;
            align-items: flex-end;
            padding: 10px 14px;
            gap: 8px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .input-pill:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-glow);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: inherit;
            font-size: 14.5px;
            line-height: 22px;
            max-height: 120px;
            height: 22px;
            resize: none;
            outline: none;
        }
        textarea::placeholder { color: #64748b; }

        .btn-icon {
            background: transparent;
            border: none;
            color: var(--text-sub);
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: color 0.2s;
            flex-shrink: 0;
        }
        .btn-icon:hover { color: #fff; }

        .btn-send {
            background: var(--accent);
            color: #080b11;
            font-weight: 700;
        }
        .btn-send:hover { background: #7dd3fc; color: #080b11; }
        .btn-send:disabled { background: #1e2638; color: #64748b; cursor: not-allowed; }

        .listening {
            color: var(--alarm-red) !important;
            animation: pulse-mic 1s infinite alternate;
        }
        @keyframes pulse-mic { from { opacity: 0.4; } to { opacity: 1; } }

        /* Alarm Modal */
        .alarm-modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(8px);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }

        .alarm-box {
            background: #111726;
            border: 2px solid var(--alarm-red);
            border-radius: 16px;
            padding: 32px;
            text-align: center;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 0 50px rgba(239, 68, 68, 0.4);
        }
        .alarm-box h3 { color: var(--alarm-red); font-size: 20px; margin-bottom: 8px; }
        .alarm-box p { font-size: 16px; margin-bottom: 22px; font-weight: 600; }
        .btn-dismiss {
            background: var(--alarm-red);
            color: #fff;
            border: none;
            padding: 10px 24px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand-container">
            <div class="brand-logo">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                DevFlow AI
            </div>
            <div class="persona-badge">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
                <select id="persona-select" class="persona-select">
                    <option value="code_architect">Mode: Code Architect</option>
                    <option value="dsa_tutor">Mode: DSA & Complexity Tutor</option>
                    <option value="personal_companion">Mode: Personal Assistant</option>
                </select>
            </div>
        </div>

        <div class="header-controls">
            <span class="user-tag">Engineer: <span>{{ username }}</span></span>
            <button class="btn-action" onclick="exportChat()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Export .MD
            </button>
            <form action="/clear" method="POST" style="margin: 0;">
                <button type="submit" class="btn-action">Clear</button>
            </form>
            <a href="/logout" class="btn-action btn-danger">Log Out</a>
        </div>
    </header>

    <div class="workspace">
        <!-- Sidebar Alarms -->
        <aside>
            <div class="sidebar-header">
                <span>Alarms & Tasks</span>
                <span id="active-count" style="color:var(--accent);">0</span>
            </div>

            <form id="alarm-form" class="alarm-form">
                <input type="text" id="rem-title" placeholder="Alarm Title (e.g. Sync review)" required>
                <input type="time" id="rem-time" required>
                <button type="submit" class="btn-add-alarm">+ Set Alarm</button>
            </form>

            <div class="reminders-list" id="reminders-list">
                <!-- Dynamically loaded -->
            </div>
        </aside>

        <!-- Main Stream Workspace -->
        <main>
            <div class="chat-scroll" id="scroll-box">
                <div class="feed-container" id="feed-container">
                    {% if not history %}
                        <div class="msg-row msg-ai">
                            <div class="msg-role">DevFlow Core</div>
                            <div class="msg-bubble">
                                <p>Welcome, <strong>{{ username }}</strong>. Workspace online. You can ask for code reviews, architectural blueprints, or use voice input to speak commands.</p>
                            </div>
                        </div>
                    {% endif %}

                    {% for message in history %}
                        {% if message.role == 'user' %}
                            <div class="msg-row msg-user">
                                <div class="msg-role">You</div>
                                <div class="msg-bubble">{{ message.text }}</div>
                            </div>
                        {% else %}
                            <div class="msg-row msg-ai">
                                <div class="msg-role">DevFlow Core</div>
                                <div class="msg-bubble rendered-msg">{{ message.text }}</div>
                            </div>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>

            <div class="dock-bar">
                <div class="dock-content">
                    <div class="chips-row">
                        <button type="button" class="prompt-chip" onclick="setPrompt('Implement a thread-safe Singleton in Java with explanation')">☕ Java Singleton</button>
                        <button type="button" class="prompt-chip" onclick="setPrompt('Design an LRU Cache with O(1) get and put in Java')">⚡ LRU Cache</button>
                        <button type="button" class="prompt-chip" onclick="setPrompt('Explain differences between TCP and UDP with latency trade-offs')">🌐 TCP vs UDP</button>
                    </div>

                    <form id="chat-form" class="input-pill">
                        <button type="button" id="mic-btn" class="btn-icon" title="Voice Input (Speech-to-Text)">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                        </button>

                        <textarea id="prompt" rows="1" placeholder="Type prompt or use mic to dictate..."></textarea>

                        <button type="submit" id="send-btn" class="btn-icon btn-send" title="Send message">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                        </button>
                    </form>
                </div>
            </div>
        </main>
    </div>

    <!-- Alarm Ring Modal -->
    <div class="alarm-modal" id="alarm-modal">
        <div class="alarm-box">
            <h3>⏰ ALARM RINGING</h3>
            <p id="alarm-desc">Task notification</p>
            <button class="btn-dismiss" onclick="dismissAlarm()">Dismiss Alarm</button>
        </div>
    </div>

    <script>
        const scrollBox = document.getElementById('scroll-box');
        const feed = document.getElementById('feed-container');
        const promptInput = document.getElementById('prompt');
        const form = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');
        const micBtn = document.getElementById('mic-btn');
        const personaSelect = document.getElementById('persona-select');

        function scrollToBottom() { scrollBox.scrollTop = scrollBox.scrollHeight; }
        scrollToBottom();

        // Enhance Code Blocks with Copy Feature
        function formatMarkdownAndCode(el) {
            el.innerHTML = marked.parse(el.textContent);
            el.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
                
                const pre = block.parentElement;
                if (!pre.parentElement.classList.contains('code-container')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'code-container';
                    
                    const header = document.createElement('div');
                    header.className = 'code-header';
                    header.innerHTML = `
                        <span>${block.className.replace('hljs ', '').replace('language-', '') || 'code'}</span>
                        <button class="copy-code-btn" onclick="copySnippet(this)">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            Copy
                        </button>
                    `;
                    pre.parentNode.insertBefore(wrapper, pre);
                    wrapper.appendChild(header);
                    wrapper.appendChild(pre);
                }
            });
        }

        document.querySelectorAll('.rendered-msg').forEach(formatMarkdownAndCode);

        function copySnippet(btn) {
            const code = btn.closest('.code-container').querySelector('code').innerText;
            navigator.clipboard.writeText(code);
            btn.innerHTML = '✓ Copied!';
            setTimeout(() => {
                btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy`;
            }, 1800);
        }

        function setPrompt(text) {
            promptInput.value = text;
            promptInput.focus();
            autoResize();
        }

        promptInput.addEventListener('input', autoResize);
        function autoResize() {
            promptInput.style.height = 'auto';
            promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + 'px';
        }

        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });

        // ---------------- STREAMING PIPELINE ---------------- //
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = promptInput.value.trim();
            if (!text) return;

            const userRow = document.createElement('div');
            userRow.className = 'msg-row msg-user';
            userRow.innerHTML = `<div class="msg-role">You</div><div class="msg-bubble">${escapeHtml(text)}</div>`;
            feed.appendChild(userRow);

            promptInput.value = '';
            promptInput.style.height = '22px';
            scrollToBottom();

            const aiRow = document.createElement('div');
            aiRow.className = 'msg-row msg-ai';
            aiRow.innerHTML = `<div class="msg-role">DevFlow Core</div><div class="msg-bubble stream-target"><span style="color:#64748b; font-style:italic;">Synthesizing response...</span></div>`;
            feed.appendChild(aiRow);
            scrollToBottom();

            const streamTarget = aiRow.querySelector('.stream-target');
            sendBtn.disabled = true;

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'prompt=' + encodeURIComponent(text) + '&persona=' + encodeURIComponent(personaSelect.value)
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullResponse = "";

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    fullResponse += decoder.decode(value, { stream: true });
                    streamTarget.innerHTML = marked.parse(fullResponse);
                    scrollToBottom();
                }

                formatMarkdownAndCode(streamTarget);
                scrollToBottom();

                await fetch('/save_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_prompt: text, ai_response: fullResponse })
                });

            } catch (err) {
                streamTarget.innerHTML = `<span style="color:#ef4444;">Connection failed. Retry in a moment.</span>`;
            } finally {
                sendBtn.disabled = false;
            }
        });

        // ---------------- WEB SPEECH API (VOICE TO TEXT) ---------------- //
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            micBtn.addEventListener('click', () => {
                if (micBtn.classList.contains('listening')) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });

            recognition.onstart = () => { micBtn.classList.add('listening'); };
            recognition.onend = () => { micBtn.classList.remove('listening'); };
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                promptInput.value = (promptInput.value + ' ' + transcript).trim();
                autoResize();
                promptInput.focus();
            };
        } else {
            micBtn.style.display = 'none';
        }

        // ---------------- EXPORT CHAT (.MD) ---------------- //
        function exportChat() {
            let markdownContent = "# DevFlow AI - Session Transcript\\n\\n";
            document.querySelectorAll('.msg-row').forEach(row => {
                const role = row.querySelector('.msg-role').innerText;
                const body = row.querySelector('.msg-bubble').innerText;
                markdownContent += `### ${role}\\n${body}\\n\\n---\\n\\n`;
            });

            const blob = new Blob([markdownContent], { type: 'text/markdown' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `DevFlow_Transcript_${new Date().toISOString().slice(0,10)}.md`;
            link.click();
        }

        // ---------------- ALARMS & AUDIO BUZZER ---------------- //
        let currentAlarmId = null;
        let audioCtx = null;
        let alarmLoop = null;

        function playSynthesizerBeep() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.3);
        }

        async function loadReminders() {
            const res = await fetch('/api/reminders');
            const list = await res.json();
            const listContainer = document.getElementById('reminders-list');
            listContainer.innerHTML = '';
            document.getElementById('active-count').textContent = list.length;

            list.forEach(item => {
                const card = document.createElement('div');
                card.className = 'reminder-card';
                card.innerHTML = `
                    <div class="reminder-info">
                        <span class="reminder-title">${escapeHtml(item.title)}</span>
                        <span class="reminder-clock">⏰ ${item.remind_time}</span>
                    </div>
                    <button class="reminder-del" onclick="deleteReminder(${item.id})">✕</button>
                `;
                listContainer.appendChild(card);
            });
            checkAlarms(list);
        }

        document.getElementById('alarm-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = document.getElementById('rem-title').value;
            const remind_time = document.getElementById('rem-time').value;

            await fetch('/api/reminders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, remind_time })
            });

            document.getElementById('rem-title').value = '';
            document.getElementById('rem-time').value = '';
            loadReminders();
        });

        async function deleteReminder(id) {
            await fetch('/api/reminders/' + id, { method: 'DELETE' });
            loadReminders();
        }

        function checkAlarms(reminders) {
            const now = new Date();
            const currentFormatted = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

            reminders.forEach(r => {
                if (r.remind_time === currentFormatted && !r.is_dismissed && !currentAlarmId) {
                    currentAlarmId = r.id;
                    document.getElementById('alarm-desc').textContent = `${r.title} (${r.remind_time})`;
                    document.getElementById('alarm-modal').style.display = 'flex';
                    playSynthesizerBeep();
                    alarmLoop = setInterval(playSynthesizerBeep, 800);
                }
            });
        }

        async function dismissAlarm() {
            if (alarmLoop) clearInterval(alarmLoop);
            document.getElementById('alarm-modal').style.display = 'none';

            if (currentAlarmId) {
                await fetch('/api/reminders/' + currentAlarmId + '/dismiss', { method: 'POST' });
                currentAlarmId = null;
            }
            loadReminders();
        }

        setInterval(loadReminders, 5000);
        loadReminders();

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
    </script>
</body>
</html>
"""

# ----------------- AUTH ROUTES ----------------- #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return render_template_string(AUTH_TEMPLATE, mode_title="Create New Account", btn_text="Register", is_login=False, error="Fields cannot be blank")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return render_template_string(AUTH_TEMPLATE, mode_title="Create New Account", btn_text="Register", is_login=False, error="Username is taken")

        hashed_pw = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template_string(AUTH_TEMPLATE, mode_title="Create New Account", btn_text="Register", is_login=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['history'] = []
            return redirect(url_for('home'))

        return render_template_string(AUTH_TEMPLATE, mode_title="Sign in to Workspace", btn_text="Sign In", is_login=True, error="Invalid credentials")

    return render_template_string(AUTH_TEMPLATE, mode_title="Sign in to Workspace", btn_text="Sign In", is_login=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- MAIN CORE & STREAMING ----------------- #
@app.route("/", methods=["GET"])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'history' not in session:
        session['history'] = []

    return render_template_string(APP_TEMPLATE, history=session['history'], username=session.get('username'))

@app.route("/generate", methods=["POST"])
def generate():
    if 'user_id' not in session:
        return Response("Unauthorized", status=401)

    user_prompt = request.form.get("prompt", "")
    persona = request.form.get("persona", "code_architect")

    personas_map = {
        "code_architect": "You are DevFlow Code Architect. Provide clean, production-grade, highly maintainable code with strict architectural patterns and zero unnecessary fluff.",
        "dsa_tutor": "You are DevFlow DSA Specialist. Break down algorithmic problems systematically with time/space complexities (Big O), edge cases, and step-by-step logic in Java.",
        "personal_companion": "You are DevFlow Virtual Companion. Help the developer organize their day, prioritize tasks, debug problems calmly, and provide crisp technical answers."
    }

    system_instruction = personas_map.get(persona, personas_map["code_architect"])

    if 'history' not in session:
        session['history'] = []

    gemini_contents = []
    for h in session['history']:
        role = "user" if h['role'] == 'user' else "model"
        gemini_contents.append({"role": role, "parts": [{"text": h['text']}]})
    gemini_contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    def generate_stream():
        models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        success = False

        for model_name in models_to_try:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=gemini_contents,
                    config={"system_instruction": system_instruction}
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                success = True
                break
            except Exception as e:
                err_text = str(e)
                if "503" in err_text or "UNAVAILABLE" in err_text or "ResourceExhausted" in err_text:
                    continue
                else:
                    yield f"Error generating response: {err_text}"
                    return

        if not success:
            yield "AI service is currently under peak global traffic. Please retry in 5 seconds."

    return Response(generate_stream(), mimetype='text/plain')

@app.route("/save_message", methods=["POST"])
def save_message():
    if 'user_id' not in session:
        return jsonify({"status": "error"}), 401

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

    return jsonify({"status": "ok"})

@app.route("/clear", methods=["POST"])
def clear():
    session.pop('history', None)
    return redirect(url_for('home'))

# ----------------- ALARM APIS ----------------- #
@app.route("/api/reminders", methods=["GET"])
def get_reminders():
    if 'user_id' not in session:
        return jsonify([]), 401

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, remind_time, is_dismissed FROM reminders WHERE user_id = ? ORDER BY remind_time ASC", (session['user_id'],))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/reminders", methods=["POST"])
def add_reminder():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    remind_time = data.get("remind_time", "").strip()

    if not title or not remind_time:
        return jsonify({"error": "Missing parameters"}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO reminders (user_id, title, remind_time) VALUES (?, ?, ?)", (session['user_id'], title, remind_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "created"}), 201

@app.route("/api/reminders/<int:rem_id>", methods=["DELETE"])
def delete_reminder(rem_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (rem_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route("/api/reminders/<int:rem_id>/dismiss", methods=["POST"])
def dismiss_reminder(rem_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE reminders SET is_dismissed = 1 WHERE id = ? AND user_id = ?", (rem_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "dismissed"})

if __name__ == "__main__":
    app.run(debug=True)