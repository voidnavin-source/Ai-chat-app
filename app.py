from flask import Flask, render_template_string, request, Response, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from google.genai import types
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'devflow_siltstone_edition_2026')

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
    <title>DevFlow AI - Access</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #FAF7EE;
            --bg-card: #FFFFFF;
            --border-card: #E8E0CE;
            --accent: #FFB16E;
            --accent-hover: #F29E54;
            --text-main: #24211D;
            --text-sub: #7A7264;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-page);
            background-image: radial-gradient(circle at 50% 0%, rgba(255, 177, 110, 0.15) 0%, transparent 60%);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .auth-card {
            width: 100%;
            max-width: 400px;
            padding: 42px 34px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 24px;
            box-shadow: 0 20px 45px rgba(203, 189, 147, 0.28);
        }
        .auth-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 22px;
            font-weight: 700;
            color: #C08A3E;
            letter-spacing: -0.4px;
            margin-bottom: 6px;
        }
        .auth-sub {
            text-align: center;
            font-size: 13.5px;
            color: var(--text-sub);
            margin-bottom: 28px;
        }
        .input-group { margin-bottom: 18px; }
        label {
            display: block;
            font-size: 12px;
            color: var(--text-sub);
            margin-bottom: 7px;
            font-weight: 600;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        input {
            width: 100%;
            background: #FDFBF7;
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 12px 14px;
            color: var(--text-main);
            font-size: 14.5px;
            outline: none;
            transition: all 0.2s ease;
        }
        input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(255, 177, 110, 0.25);
            background: #FFFFFF;
        }
        button {
            width: 100%;
            background: var(--accent);
            color: #261D12;
            border: none;
            padding: 13px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14.5px;
            cursor: pointer;
            margin-top: 10px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px rgba(255, 177, 110, 0.35);
        }
        button:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
        }
        .switch-link {
            text-align: center;
            margin-top: 22px;
            font-size: 13px;
            color: var(--text-sub);
        }
        .switch-link a { color: #C08A3E; text-decoration: none; font-weight: 600; }
        .error-msg {
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.25);
            color: #DC2626;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            margin-bottom: 18px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="auth-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
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
                Need an account? <a href="/register">Sign Up</a>
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
    <title>DevFlow AI - Personal Assistant</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        :root {
            --bg-canvas: #FAF7EE;
            --bg-sidebar: #F4EEDC;
            --bg-card: #FFFFFF;
            --border-warm: #E6DCBF;
            --border-subtle: #EBE4D1;
            --text-heading: #26231E;
            --text-body: #3D3830;
            --text-muted: #7E7566;
            --accent-warm: #FFB16E;
            --accent-ochre: #CCA25A;
            --accent-ochre-dark: #A97E32;
            --user-bubble: #F0E8D0;
            --danger: #E11D48;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-body);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* Warm Cream Glass Header */
        header {
            height: 62px;
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(250, 247, 238, 0.92);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-warm);
            z-index: 30;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .brand-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: -0.3px;
        }

        .brand-badge svg { color: var(--accent-ochre-dark); }

        .persona-container {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            border-radius: 999px;
            padding: 3px 12px;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 6px rgba(203, 189, 147, 0.15);
        }

        .persona-dot {
            width: 7px;
            height: 7px;
            background: var(--accent-warm);
            border-radius: 50%;
            box-shadow: 0 0 6px var(--accent-warm);
        }

        .persona-select {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 600;
            outline: none;
            cursor: pointer;
            font-family: inherit;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .user-pill {
            font-size: 12.5px;
            color: var(--text-muted);
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            padding: 5px 12px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(203, 189, 147, 0.1);
        }
        .user-pill strong { color: var(--text-heading); font-weight: 600; }

        .header-btn {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(203, 189, 147, 0.1);
        }

        .header-btn:hover {
            color: var(--text-heading);
            border-color: var(--accent-ochre);
            background: #FBF9F2;
        }

        .header-btn-danger:hover {
            color: var(--danger);
            border-color: rgba(225, 29, 72, 0.3);
            background: rgba(225, 29, 72, 0.05);
        }

        /* Workspace Core Layout */
        .workspace {
            display: flex;
            flex: 1;
            height: calc(100vh - 62px);
            overflow: hidden;
        }

        /* Siltstone Warm Sidebar */
        aside {
            width: 300px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border-warm);
            display: flex;
            flex-direction: column;
            padding: 22px 18px;
            gap: 20px;
        }

        .sidebar-title-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-warm);
        }

        .sidebar-title {
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--accent-ochre-dark);
        }

        .counter-badge {
            background: #FFF5B8;
            color: var(--accent-ochre-dark);
            border: 1px solid var(--border-warm);
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 12px;
        }

        .task-input-card {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            border-radius: 14px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            box-shadow: 0 4px 15px rgba(203, 189, 147, 0.2);
        }

        .task-input-card input {
            background: #FDFCF9;
            border: 1px solid var(--border-warm);
            color: var(--text-heading);
            padding: 10px 12px;
            border-radius: 9px;
            font-size: 13px;
            outline: none;
            transition: all 0.2s ease;
        }

        .task-input-card input:focus {
            border-color: var(--accent-warm);
            background: #FFFFFF;
            box-shadow: 0 0 0 3px rgba(255, 177, 110, 0.2);
        }

        .btn-set-alarm {
            background: var(--accent-warm);
            color: #261D12;
            border: none;
            padding: 9px;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(255, 177, 110, 0.35);
        }

        .btn-set-alarm:hover {
            background: #F29E54;
            transform: translateY(-1px);
        }

        .reminders-viewport {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .reminders-viewport::-webkit-scrollbar { width: 4px; }
        .reminders-viewport::-webkit-scrollbar-thumb { background: var(--border-warm); border-radius: 2px; }

        .empty-tasks {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            gap: 8px;
            height: 140px;
            font-size: 12.5px;
            text-align: center;
        }

        .empty-tasks svg { opacity: 0.5; color: var(--accent-ochre); }

        .task-item {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            border-radius: 12px;
            padding: 12px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 6px rgba(203, 189, 147, 0.15);
            transition: border-color 0.2s ease;
        }

        .task-item:hover { border-color: var(--accent-ochre); }

        .task-details {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .task-name { font-size: 13px; font-weight: 600; color: var(--text-heading); }
        .task-timestamp { font-size: 11.5px; color: var(--accent-ochre-dark); font-family: 'JetBrains Mono', monospace; font-weight: 600; }

        .task-delete-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 6px;
            transition: all 0.2s ease;
        }

        .task-delete-btn:hover {
            color: var(--danger);
            background: rgba(225, 29, 72, 0.08);
        }

        /* Warm Canvas Chat Area */
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
            background: var(--bg-canvas);
        }

        .chat-scroll-feed {
            flex: 1;
            overflow-y: auto;
            scroll-behavior: smooth;
            padding: 34px 28px 180px 28px;
        }

        .chat-scroll-feed::-webkit-scrollbar { width: 6px; }
        .chat-scroll-feed::-webkit-scrollbar-thumb { background: var(--border-warm); border-radius: 3px; }

        .messages-container {
            max-width: 820px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 32px;
        }

        .message-row {
            display: flex;
            flex-direction: column;
            width: 100%;
        }

        .message-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .row-user { align-items: flex-end; }
        .row-user .message-meta { color: var(--accent-ochre-dark); }
        .row-user .bubble-box {
            background: var(--user-bubble);
            border: 1px solid var(--border-warm);
            border-radius: 18px 18px 4px 18px;
            padding: 14px 20px;
            max-width: 82%;
            font-size: 14.5px;
            line-height: 1.65;
            color: var(--text-heading);
            box-shadow: 0 4px 14px rgba(203, 189, 147, 0.22);
        }

        .row-ai { align-items: flex-start; }
        .ai-role-tag {
            background: #FFF5B8;
            color: var(--accent-ochre-dark);
            border: 1px solid var(--border-warm);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }

        .row-ai .bubble-box {
            width: 100%;
            font-size: 15px;
            line-height: 1.72;
            color: var(--text-body);
        }

        .bubble-box p { margin-bottom: 12px; }
        .bubble-box p:last-child { margin-bottom: 0; }
        .bubble-box ul, .bubble-box ol { margin: 8px 0 14px 22px; }
        .bubble-box li { margin-bottom: 5px; }

        /* Code Blocks - GitHub Classic Warm Integration */
        .code-container {
            position: relative;
            margin: 16px 0;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-warm);
            background: #FFFFFF;
            box-shadow: 0 4px 18px rgba(203, 189, 147, 0.25);
        }

        .code-header {
            background: #F8F5EB;
            padding: 8px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11.5px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-warm);
        }

        .copy-code-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 11.5px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-weight: 600;
            transition: color 0.2s ease;
        }
        .copy-code-btn:hover { color: var(--text-heading); }

        pre {
            background: #FCFAF5 !important;
            padding: 16px;
            overflow-x: auto;
            margin: 0 !important;
        }

        code { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; }
        p code {
            background: #FFF5B8;
            color: #8C6219;
            border: 1px solid #EAE0C7;
            padding: 2px 6px;
            border-radius: 5px;
            font-size: 13px;
        }

        /* Warm Floating Dock */
        .input-dock {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background: linear-gradient(180deg, rgba(250, 247, 238, 0) 0%, rgba(250, 247, 238, 0.94) 28%, #FAF7EE 100%);
            padding: 0 24px 26px 24px;
            display: flex;
            justify-content: center;
            z-index: 20;
        }

        .dock-shell {
            width: 100%;
            max-width: 820px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .chips-list {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            white-space: nowrap;
            scrollbar-width: none;
        }
        .chips-list::-webkit-scrollbar { display: none; }

        .chip-button {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 6px rgba(203, 189, 147, 0.15);
        }
        .chip-button:hover {
            color: var(--text-heading);
            border-color: var(--accent-warm);
            background: #FFFBF4;
            transform: translateY(-1px);
        }

        .input-pill-box {
            background: #FFFFFF;
            border: 1px solid var(--border-warm);
            border-radius: 18px;
            display: flex;
            align-items: flex-end;
            padding: 10px 16px;
            gap: 10px;
            box-shadow: 0 8px 30px rgba(203, 189, 147, 0.35);
            transition: all 0.2s ease;
        }

        .input-pill-box:focus-within {
            border-color: var(--accent-warm);
            box-shadow: 0 0 0 3px rgba(255, 177, 110, 0.25);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-heading);
            font-family: inherit;
            font-size: 15px;
            line-height: 22px;
            max-height: 120px;
            height: 22px;
            resize: none;
            outline: none;
        }
        textarea::placeholder { color: #A69D8E; }

        .dock-action-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            width: 34px;
            height: 34px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            flex-shrink: 0;
        }
        .dock-action-btn:hover { color: var(--text-heading); background: #F8F5EB; }

        .btn-submit {
            background: var(--accent-warm);
            color: #261D12;
        }
        .btn-submit:hover {
            background: #F29E54;
            transform: scale(1.05);
        }
        .btn-submit:disabled {
            background: #E8E0CD;
            color: #A39A88;
            cursor: not-allowed;
            transform: none;
        }

        .mic-active {
            color: var(--danger) !important;
            animation: pulse-ring 1s infinite alternate;
        }
        @keyframes pulse-ring { from { opacity: 0.4; } to { opacity: 1; } }

        /* Warm Alarm Modal Overlay */
        .alarm-modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(38, 35, 30, 0.65);
            backdrop-filter: blur(8px);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }

        .alarm-card {
            background: #FFFFFF;
            border: 2px solid var(--danger);
            border-radius: 20px;
            padding: 34px;
            text-align: center;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 10px 40px rgba(225, 29, 72, 0.25);
        }
        .alarm-card h3 { color: var(--danger); font-size: 20px; margin-bottom: 8px; }
        .alarm-card p { font-size: 16px; margin-bottom: 24px; font-weight: 600; color: var(--text-heading); }
        .btn-dismiss {
            background: var(--danger);
            color: #fff;
            border: none;
            padding: 11px 26px;
            border-radius: 10px;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }
        .btn-dismiss:hover { opacity: 0.9; }
    </style>
</head>
<body>

    <header>
        <div class="header-left">
            <div class="brand-badge">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                DevFlow AI
            </div>
            <div class="persona-container">
                <span class="persona-dot"></span>
                <select id="persona-select" class="persona-select">
                    <option value="code_architect">Role: Code Architect</option>
                    <option value="dsa_tutor">Role: DSA & Complexity Tutor</option>
                    <option value="personal_companion">Role: Personal Assistant</option>
                </select>
            </div>
        </div>

        <div class="header-right">
            <div class="user-pill">Engineer: <strong>{{ username }}</strong></div>
            <button class="header-btn" onclick="exportChat()">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Export .MD
            </button>
            <form action="/clear" method="POST" style="margin: 0;">
                <button type="submit" class="header-btn">Clear</button>
            </form>
            <a href="/logout" class="header-btn header-btn-danger">Log Out</a>
        </div>
    </header>

    <div class="workspace">
        <aside>
            <div class="sidebar-title-bar">
                <span class="sidebar-title">Alarms & Schedule</span>
                <span id="active-count" class="counter-badge">0</span>
            </div>

            <form id="alarm-form" class="task-input-card">
                <input type="text" id="rem-title" placeholder="Reminder title..." required>
                <input type="time" id="rem-time" required>
                <button type="submit" class="btn-set-alarm">+ Set Alarm</button>
            </form>

            <div class="reminders-viewport" id="reminders-list">
                <!-- Dynamically loaded -->
            </div>
        </aside>

        <main>
            <div class="chat-scroll-feed" id="scroll-box">
                <div class="messages-container" id="messages-container">
                    {% if not history %}
                        <div class="message-row row-ai">
                            <div class="message-meta">
                                <span class="ai-role-tag">DevFlow Core</span>
                            </div>
                            <div class="bubble-box">
                                <p>Welcome, <strong>{{ username }}</strong>. Workspace ready. Ask me to design scalable architecture, analyze algorithms, or dictate instructions using the mic.</p>
                            </div>
                        </div>
                    {% endif %}

                    {% for message in history %}
                        {% if message.role == 'user' %}
                            <div class="message-row row-user">
                                <div class="message-meta">You</div>
                                <div class="bubble-box">{{ message.text }}</div>
                            </div>
                        {% else %}
                            <div class="message-row row-ai">
                                <div class="message-meta">
                                    <span class="ai-role-tag">DevFlow Core</span>
                                </div>
                                <div class="bubble-box rendered-content">{{ message.text }}</div>
                            </div>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>

            <div class="input-dock">
                <div class="dock-shell">
                    <div class="chips-list">
                        <button type="button" class="chip-button" onclick="setPrompt('Implement a thread-safe Singleton in Java with explanation')">☕ Java Singleton</button>
                        <button type="button" class="chip-button" onclick="setPrompt('Design an LRU Cache with O(1) get and put in Java')">⚡ LRU Cache (Java)</button>
                        <button type="button" class="chip-button" onclick="setPrompt('Explain differences between TCP and UDP with latency trade-offs')">🌐 TCP vs UDP</button>
                    </div>

                    <form id="chat-form" class="input-pill-box">
                        <button type="button" id="mic-btn" class="dock-action-btn" title="Voice Input">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                        </button>

                        <textarea id="prompt" rows="1" placeholder="Type a message or use speech-to-text..."></textarea>

                        <button type="submit" id="send-btn" class="dock-action-btn btn-submit" title="Send">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                        </button>
                    </form>
                </div>
            </div>
        </main>
    </div>

    <!-- Active Alarm Modal Overlay -->
    <div class="alarm-modal" id="alarm-modal">
        <div class="alarm-card">
            <h3>⏰ ALARM RINGING</h3>
            <p id="alarm-desc">Task notification</p>
            <button class="btn-dismiss" onclick="dismissAlarm()">Dismiss Alarm</button>
        </div>
    </div>

    <script>
        const scrollBox = document.getElementById('scroll-box');
        const container = document.getElementById('messages-container');
        const promptInput = document.getElementById('prompt');
        const form = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');
        const micBtn = document.getElementById('mic-btn');
        const personaSelect = document.getElementById('persona-select');

        function scrollToBottom() { scrollBox.scrollTop = scrollBox.scrollHeight; }
        scrollToBottom();

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
                        <span>${block.className.replace('hljs ', '').replace('language-', '') || 'snippet'}</span>
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

        document.querySelectorAll('.rendered-content').forEach(formatMarkdownAndCode);

        function copySnippet(btn) {
            const code = btn.closest('.code-container').querySelector('code').innerText;
            navigator.clipboard.writeText(code);
            btn.innerHTML = '✓ Copied';
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
            userRow.className = 'message-row row-user';
            userRow.innerHTML = `<div class="message-meta">You</div><div class="bubble-box">${escapeHtml(text)}</div>`;
            container.appendChild(userRow);

            promptInput.value = '';
            promptInput.style.height = '22px';
            scrollToBottom();

            const aiRow = document.createElement('div');
            aiRow.className = 'message-row row-ai';
            aiRow.innerHTML = `<div class="message-meta"><span class="ai-role-tag">DevFlow Core</span></div><div class="bubble-box stream-target"><span style="color:#7E7566; font-style:italic;">Processing query...</span></div>`;
            container.appendChild(aiRow);
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
                streamTarget.innerHTML = `<span style="color:#E11D48;">Connection failed. Retry in a moment.</span>`;
            } finally {
                sendBtn.disabled = false;
            }
        });

        // ---------------- WEB SPEECH API ---------------- //
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            micBtn.addEventListener('click', () => {
                if (micBtn.classList.contains('mic-active')) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });

            recognition.onstart = () => { micBtn.classList.add('mic-active'); };
            recognition.onend = () => { micBtn.classList.remove('mic-active'); };
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
            document.querySelectorAll('.message-row').forEach(row => {
                const role = row.querySelector('.message-meta').innerText;
                const body = row.querySelector('.bubble-box').innerText;
                markdownContent += `### ${role}\\n${body}\\n\\n---\\n\\n`;
            });

            const blob = new Blob([markdownContent], { type: 'text/markdown' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `DevFlow_Transcript_${new Date().toISOString().slice(0,10)}.md`;
            link.click();
        }

        // ---------------- ALARMS & AUDIO ENGINE ---------------- //
        let currentAlarmId = null;
        let audioCtx = null;
        let alarmLoop = null;

        function playSynthesizerBeep() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
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

            if (list.length === 0) {
                listContainer.innerHTML = `
                    <div class="empty-tasks">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        <span>No active alarms</span>
                    </div>
                `;
                return;
            }

            list.forEach(item => {
                const card = document.createElement('div');
                card.className = 'task-item';
                card.innerHTML = `
                    <div class="task-details">
                        <span class="task-name">${escapeHtml(item.title)}</span>
                        <span class="task-timestamp">⏰ ${item.remind_time}</span>
                    </div>
                    <button class="task-delete-btn" onclick="deleteReminder(${item.id})">✕</button>
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
        models_to_try = [
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash"
        ]
        
        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )

        streamed_anything = False

        for model_name in models_to_try:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=gemini_contents,
                    config=gen_config
                )
                for chunk in response:
                    if chunk.text:
                        streamed_anything = True
                        yield chunk.text
                
                if streamed_anything:
                    return
            except Exception as e:
                err_text = str(e)
                if any(k in err_text for k in ["503", "UNAVAILABLE", "ResourceExhausted", "429", "404"]):
                    continue
                else:
                    yield f"Error: {err_text}"
                    return

        if not streamed_anything:
            yield "All models are currently facing traffic spikes. Please retry your message in 5 seconds."

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