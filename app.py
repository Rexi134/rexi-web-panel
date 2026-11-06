#!/usr/bin/env python3
"""
REXI'S WEB PANEL  —  Flask + Instagrapi Edition
"""
import os, re, sys, time, random, threading, hashlib
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, ClientError, FeedbackRequired,
    LoginRequired, PleaseWaitFewMinutes, RateLimitError
)

# ─────────────────────────── CONFIG ───────────────────────────
SECRET_KEY = "REXI_WEB_PANEL_SECRET"
ACCESS_KEY = "Rexi_Master_Penal"

# Burst Settings
BURST_SIZE = 40           
BURST_GAP = 0.08          
BURST_COOLDOWN = 3.0      

# ─────────────────────── DEVICE SPOOFING ──────────────────────
DEVICES = [
    ("Xiaomi", "M2101K6G", "sweet", 31, "12", 440, "1080x2260"),
    ("samsung", "SM-A528B", "a52sxq", 33, "13", 420, "1080x2400"),
    ("OnePlus", "LE2101", "oneplusrt", 31, "12", 480, "1080x2260"),
    ("Google", "Pixel 6", "oriole", 33, "13", 420, "1080x2400"),
    ("realme", "RMX3360", "ree6942", 31, "12", 440, "1080x2400"),
]

def get_device(seed):
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    m, model, dev, av, ar, dpi, res = rng.choice(DEVICES)
    return {"manufacturer": m, "model": model, "device": dev, "android_version": av, "android_release": ar, "dpi": f"{dpi}dpi", "resolution": res}

def get_uuids(seed):
    h = hashlib.sha256(("uuid:" + seed).encode()).digest()
    g = lambda i, n: h[i:i+n].hex()
    return {"uuid": f"{g(0,4)}-{g(4,2)}-{g(6,2)}-{g(8,2)}-{g(10,6)}", "phone_id": f"{g(16,4)}-{g(20,2)}-{g(22,2)}-{g(24,2)}-{g(26,6)}", "client_session_id": f"{g(32,4)}-{g(36,2)}-{g(38,2)}-{g(40,2)}-{g(42,6)}", "advertising_id": f"{g(48,4)}-{g(52,2)}-{g(54,2)}-{g(56,2)}-{g(58,6)}"}

def get_ua(d):
    return (f"Instagram 269.0.0.18.75 Android ({d['android_version']}/{d['android_release']}; {d['dpi']}; {d['resolution']}; {d['manufacturer']}; {d['model']}; {d['device']}; en_US; 319244081)")

def build_client(sessionid):
    cl = Client()
    dev = get_device(sessionid)
    try:
        cl.set_device(dev)
        cl.set_uuids(get_uuids(sessionid))
    except AttributeError: pass
    cl.set_locale("en_US")
    cl.set_user_agent(get_ua(dev))
    return cl

# ─────────────────────── PAYLOADS ────────────────────────
FLAG_EMOJIS = ["🏴‍☠️", "🇦🇨", "🇦🇩", "🇦🇪", "🇦🇫", "🇦🇬", "🇦🇮", "🇦🇱", "🇦🇲", "🇦🇴", "🇦🇶", "🇦🇷", "🇦🇸", "🇦🇹", "🇦🇺", "🇦🇼", "🇦🇽", "🇦🇿", "🇧🇦", "🇧🇧", "🇧🇩", "🇧🇪", "🇧🇫", "🇧🇬", "🇧🇭", "🇧🇮", "🇧🇯", "🇧🇱", "🇧🇲", "🇧🇳", "🇧🇴", "🇧🇶", "🇧🇷", "🇧🇸", "🇧🇹", "🇧🇻", "🇧🇼", "🇧🇾", "🇧🇿", "🇨🇦"]
BASE_LINE = "{target}    Ƭᴇʀɪ Mᴀᴀ Ƙᴀ Ɓʜᴏsᴅᴀ {emoji}"

# ─────────────────────── FLASK APP & STATE ───────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

state = {
    "sessions": [],      # list of {"session_id", "username", "client"}
    "target": "",
    "thread_id": "",
    "group_name": "",
    "running": False,
    "total_sent": 0,
    "logs": []           # list of recent log messages
}

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    state["logs"].insert(0, f"[{timestamp}] {msg}")
    if len(state["logs"]) > 50: state["logs"].pop()

# ─────────────────────── SPAM ENGINE ─────────────────────────
def spam_worker():
    global state
    while state["running"]:
        if not state["sessions"] or not state["thread_id"] or not state["target"]:
            time.sleep(1)
            continue
            
        for s in list(state["sessions"]):
            if not state["running"]: break
            
            client = s["client"]
            uname = s["username"]
            
            burst_sent = 0
            for _ in range(BURST_SIZE):
                if not state["running"]: break
                
                try:
                    emoji = random.choice(FLAG_EMOJIS)
                    msg = "\n\n".join([BASE_LINE.replace("{target}", state["target"]).replace("{emoji}", emoji) for _ in range(16)])
                    msg += "\u200b" * random.randint(1, 4)
                    
                    client.direct_send(msg, thread_ids=[int(state["thread_id"])])
                    state["total_sent"] += 1
                    burst_sent += 1
                    time.sleep(BURST_GAP)
                    
                except (RateLimitError, PleaseWaitFewMinutes, FeedbackRequired):
                    add_log(f"⚠️ {uname} hit Rate Limit. Cooling 60s.")
                    time.sleep(60)
                    break
                except Exception as e:
                    add_log(f"❌ Error on {uname}: {str(e)[:50]}")
                    time.sleep(5)
                    break
            
            if burst_sent > 0:
                time.sleep(BURST_COOLDOWN)
                
    add_log("🛑 Spam engine stopped.")

# ─────────────────────── HTML TEMPLATES ──────────────────────
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REXI PANEL - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center h-screen">
    <div class="bg-gray-800 p-8 rounded-lg shadow-lg w-96 border border-gray-700">
        <h1 class="text-2xl font-bold mb-6 text-center text-blue-400">REXI PANEL</h1>
        {% if error %}
        <div class="bg-red-500 text-white p-2 rounded mb-4 text-sm text-center">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="text" name="key" placeholder="Enter Master Key" class="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white mb-4 focus:outline-none focus:border-blue-500" required>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded transition">Verify & Login</button>
        </form>
    </div>
</body>
</html>
"""

PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REXI WEB PANEL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0b0f19; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card { background-color: #111827; border: 1px solid #1f2937; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1rem; }
        .toggle-checkbox:checked { right: 0; border-color: #10b981; }
        .toggle-checkbox:checked + .toggle-label { background-color: #10b981; }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-4xl mx-auto">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-bold text-blue-500">REXI WEB PANEL</h1>
            <a href="/logout" class="text-red-400 hover:text-red-300 text-sm">Logout</a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Session Management -->
            <div class="card">
                <h2 class="text-lg font-semibold mb-3 text-green-400">✍🏻 Session IDs</h2>
                <div class="flex gap-2 mb-4">
                    <input type="text" id="sess_input" placeholder="Paste session ID" class="flex-1 bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm focus:outline-none focus:border-green-500">
                    <button onclick="addSession()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm font-bold transition">Add</button>
                </div>
                <div id="session_list" class="space-y-2 max-h-40 overflow-y-auto pr-2">
                    <!-- Sessions load here -->
                </div>
            </div>

            <!-- Config -->
            <div class="card">
                <h2 class="text-lg font-semibold mb-3 text-blue-400">🎯 Configuration</h2>
                <div class="mb-3">
                    <label class="block text-sm text-gray-400 mb-1">Target Name</label>
                    <input type="text" id="target_input" class="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm" onchange="saveConfig()">
                </div>
                <div class="mb-3">
                    <label class="block text-sm text-gray-400 mb-1">GC Link</label>
                    <input type="text" id="gc_input" class="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm" onchange="saveConfig()">
                </div>
            </div>
        </div>

        <!-- Controls & Stats -->
        <div class="card flex flex-col md:flex-row justify-between items-center mt-4">
            <div class="flex items-center gap-4 mb-4 md:mb-0">
                <div class="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                    <input type="checkbox" name="toggle" id="toggle" class="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer" onchange="toggleEngine()"/>
                    <label for="toggle" class="toggle-label block overflow-hidden h-6 rounded-full bg-gray-700 cursor-pointer"></label>
                </div>
                <label for="toggle" class="text-lg font-bold">ON / OFF</label>
            </div>
            
            <div class="text-right">
                <div class="text-sm text-gray-400">Total Messages Sent</div>
                <div id="total_sent" class="text-3xl font-bold text-green-400">0</div>
            </div>
        </div>

        <!-- Logs -->
        <div class="card mt-4 bg-gray-900 font-mono text-xs">
            <h2 class="text-sm font-semibold mb-2 text-gray-400">Live Logs</h2>
            <div id="logs" class="h-40 overflow-y-auto space-y-1">
                <!-- Logs load here -->
            </div>
        </div>
    </div>

    <script>
        // Load initial data
        fetch('/api/data').then(r => r.json()).then(data => {
            document.getElementById('target_input').value = data.target;
            document.getElementById('gc_input').value = data.gc_link;
            document.getElementById('toggle').checked = data.running;
            updateUI(data);
        });

        // Poll for updates every 2 seconds
        setInterval(() => {
            fetch('/api/data').then(r => r.json()).then(data => updateUI(data));
        }, 2000);

        function updateUI(data) {
            document.getElementById('total_sent').innerText = data.total_sent;
            
            // Update sessions
            const sessDiv = document.getElementById('session_list');
            sessDiv.innerHTML = '';
            data.sessions.forEach(s => {
                sessDiv.innerHTML += `
                    <div class="flex justify-between items-center bg-gray-800 p-2 rounded text-sm border border-gray-700">
                        <span class="text-green-400">@${s}</span>
                    </div>
                `;
            });
            
            // Update logs
            const logDiv = document.getElementById('logs');
            logDiv.innerHTML = '';
            data.logs.forEach(log => {
                logDiv.innerHTML += `<div class="text-gray-300">${log}</div>`;
            });
        }

        function addSession() {
            const val = document.getElementById('sess_input').value.trim();
            if(!val) return;
            document.getElementById('sess_input').value = 'Logging in...';
            
            fetch('/api/add_session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: val})
            }).then(r => r.json()).then(res => {
                document.getElementById('sess_input').value = '';
                if(!res.success) alert(res.error);
            });
        }

        function saveConfig() {
            const target = document.getElementById('target_input').value;
            const gc = document.getElementById('gc_input').value;
            
            fetch('/api/save_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target: target, gc_link: gc})
            });
        }

        function toggleEngine() {
            const isRunning = document.getElementById('toggle').checked;
            fetch('/api/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({running: isRunning})
            });
        }
    </script>
</body>
</html>
"""

# ─────────────────────── ROUTES ──────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('key') == ACCESS_KEY:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error="Invalid Key")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(PANEL_HTML)

@app.route('/api/data')
def get_data():
    if not session.get('logged_in'): return jsonify({})
    return jsonify({
        "running": state["running"],
        "total_sent": state["total_sent"],
        "target": state["target"],
        "gc_link": state["thread_id"],
        "sessions": [s["username"] for s in state["sessions"]],
        "logs": state["logs"]
    })

@app.route('/api/add_session', methods=['POST'])
def add_session():
    if not session.get('logged_in'): return jsonify({"success": False, "error": "Unauthorized"})
    data = request.json
    sid = data.get('session_id', '').strip()
    
    try:
        cl = build_client(sid)
        cl.login_by_sessionid(sid)
        info = cl.account_info()
        
        if any(s["session_id"] == sid for s in state["sessions"]):
            return jsonify({"success": False, "error": "Session already added"})
            
        state["sessions"].append({
            "session_id": sid,
            "username": info.username,
            "client": cl
        })
        add_log(f"✅ Added session @{info.username}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:100]})

@app.route('/api/save_config', methods=['POST'])
def save_config():
    if not session.get('logged_in'): return jsonify({"success": False})
    data = request.json
    state["target"] = data.get('target', '')
    gc_link = data.get('gc_link', '')
    
    m = re.search(r"(\d{15,})", gc_link)
    if m:
        state["thread_id"] = m.group(1)
        add_log(f"✅ GC Link set: {state['thread_id']}")
    else:
        state["thread_id"] = ""
        
    return jsonify({"success": True})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    if not session.get('logged_in'): return jsonify({"success": False})
    data = request.json
    
    if data.get('running'):
        if not state["sessions"]:
            return jsonify({"success": False, "error": "No sessions added"})
        if not state["target"] or not state["thread_id"]:
            return jsonify({"success": False, "error": "Config missing"})
            
        if not state["running"]:
            state["running"] = True
            add_log("🔥 Spam Engine Started")
            threading.Thread(target=spam_worker, daemon=True).start()
    else:
        state["running"] = False
        
    return jsonify({"success": True})

if __name__ == "__main__":
    print("[+] REXI WEB PANEL BOOTING...")
    print(f"[+] Access Key: {ACCESS_KEY}")
    print("[+] Server running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
