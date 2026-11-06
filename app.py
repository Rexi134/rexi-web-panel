#!/usr/bin/env python3
"""
REXI'S WEB PANEL  —  Professional Multi-User + Watchdog Engine
"""
import os, re, sys, time, random, threading, hashlib, uuid
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, ClientError, FeedbackRequired,
    LoginRequired, PleaseWaitFewMinutes, RateLimitError
)

# ─────────────────────────── CONFIG ───────────────────────────
SECRET_KEY = "REXI_WEB_PANEL_SECRET"
ACCESS_KEY = "Rexi_Master_Penal"

# Spam Settings (Constant Speed)
BURST_SIZE = 40           
BURST_GAP = 0.08          
BURST_COOLDOWN = 3.0      

# Watchdog Settings
WATCHDOG_TIMEOUT = 30 # If stalled for 30s, force restart

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

# Multi-User State Store: { browser_id: state_dict }
user_states = {}

def get_state():
    if 'browser_id' not in session:
        session['browser_id'] = str(uuid.uuid4())
    
    bid = session['browser_id']
    if bid not in user_states:
        user_states[bid] = {
            "sessions": [],
            "target": "",
            "thread_id": "",
            "running": False,
            "total_sent": 0,
            "wdt_saves": 0,
            "logs": []
        }
    return user_states[bid]

def add_log(st, msg):
    timestamp = time.strftime("%H:%M:%S")
    st["logs"].insert(0, f"[{timestamp}] {msg}")
    if len(st["logs"]) > 50: st["logs"].pop()

# ─────────────────────── WATCHDOG & SPAM ENGINE ──────────────
def watchdog_loop(st):
    """Monitors sessions. If one freezes, it force-restarts it."""
    while st.get("running"):
        time.sleep(5)
        if not st.get("running"): break
        
        now = time.time()
        for s in st["sessions"]:
            if now < s.get("cooldown_until", 0):
                s["last_send"] = now # Reset timer during cooldown so WDT doesn't trigger
                continue
                
            if now - s.get("last_send", now) > WATCHDOG_TIMEOUT:
                s["wdt_saves"] = s.get("wdt_saves", 0) + 1
                st["wdt_saves"] += 1
                add_log(st, f"🐕 Watchdog: @{s['username']} stalled. Force Restarting...")
                
                try:
                    new_cl = build_client(s["session_id"])
                    new_cl.login_by_sessionid(s["session_id"])
                    s["client"] = new_cl
                    s["last_send"] = time.time()
                    add_log(st, f"✅ Watchdog: @{s['username']} revived successfully.")
                except Exception as e:
                    add_log(st, f"❌ Watchdog failed to revive @{s['username']}")

def spam_worker(st):
    """Main Spam Loop for a specific user."""
    # Start Watchdog
    threading.Thread(target=watchdog_loop, args=(st,), daemon=True).start()
    
    while st.get("running"):
        if not st["sessions"] or not st["thread_id"] or not st["target"]:
            time.sleep(1)
            continue
            
        for s in list(st["sessions"]):
            if not st["running"] or s not in st["sessions"]: break
            
            # Skip if in cooldown
            if time.time() < s.get("cooldown_until", 0):
                continue
                
            uname = s["username"]
            client = s["client"]
            
            burst_sent = 0
            for _ in range(BURST_SIZE):
                if not st["running"] or s not in st["sessions"]: break
                
                try:
                    emoji = random.choice(FLAG_EMOJIS)
                    msg = "\n\n".join([BASE_LINE.replace("{target}", st["target"]).replace("{emoji}", emoji) for _ in range(16)])
                    msg += "\u200b" * random.randint(1, 4)
                    
                    client.direct_send(msg, thread_ids=[int(st["thread_id"])])
                    st["total_sent"] += 1
                    s["sent"] = s.get("sent", 0) + 1
                    s["last_send"] = time.time()
                    burst_sent += 1
                    
                    time.sleep(BURST_GAP)
                    
                except (RateLimitError, PleaseWaitFewMinutes, FeedbackRequired, ClientError) as e:
                    err = str(e).lower()
                    if any(k in err for k in ("limit", "wait", "spam", "block", "feedback", "item_ack")):
                        add_log(st, f"⚠️ {uname} hit Rate Limit. Cooling 60s.")
                        s["cooldown_until"] = time.time() + 60  # Max 1 minute cooldown
                    else:
                        add_log(st, f"❌ Error on {uname}: {err[:40]}")
                        s["cooldown_until"] = time.time() + 5
                    break
                    
                except Exception as e:
                    add_log(st, f"❌ Worker Error on {uname}: {str(e)[:40]}")
                    time.sleep(5)
                    break

            if burst_sent > 0:
                time.sleep(BURST_COOLDOWN)
            else:
                time.sleep(1)

    add_log(st, "🛑 Spam engine stopped.")

def start_engine(st):
    if st.get("running"): return
    st["running"] = True
    add_log(st, "🔥 Spam Engine Started")
    threading.Thread(target=spam_worker, args=(st,), daemon=True).start()

# ─────────────────────── HTML TEMPLATES ──────────────────────
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REXI PANEL - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background: #0b0f19; } </style>
</head>
<body class="text-white flex items-center justify-center h-screen bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 via-[#0b0f19] to-black">
    <div class="bg-gray-800/80 backdrop-blur-md p-8 rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.1)] w-96 border border-gray-700">
        <div class="flex justify-center mb-6">
            <div class="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/50">
                <span class="text-3xl">⚡</span>
            </div>
        </div>
        <h1 class="text-2xl font-bold mb-6 text-center text-white">REXI PANEL</h1>
        {% if error %}
        <div class="bg-red-500/20 border border-red-500 text-red-400 p-3 rounded-lg mb-4 text-sm text-center font-medium">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="password" name="key" placeholder="Enter Master Key" class="w-full bg-gray-900/50 border border-gray-700 rounded-lg p-3 text-white mb-4 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition" required>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg shadow-lg shadow-blue-500/30 transition-all active:scale-95">Verify & Login</button>
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #0b0f19; }
        .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); }
        .toggle-checkbox:checked { right: 0; border-color: #10b981; }
        .toggle-checkbox:checked + .toggle-label { background-color: #10b981; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #374151; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #4b5563; }
    </style>
</head>
<body class="p-4 md:p-8 text-gray-200 min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-800 via-[#0b0f19] to-black">
    <div class="max-w-5xl mx-auto">
        
        <!-- Header -->
        <div class="flex justify-between items-center mb-8 glass p-4 rounded-2xl">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                    <span class="text-xl">⚡</span>
                </div>
                <h1 class="text-xl font-bold text-white tracking-wide">REXI DASHBOARD</h1>
            </div>
            <a href="/logout" class="text-red-400 hover:text-white bg-red-500/10 hover:bg-red-500 px-4 py-2 rounded-lg text-sm font-medium transition-all">Logout</a>
        </div>

        <!-- Dashboard Stats -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition"><span class="text-6xl">📨</span></div>
                <h3 class="text-gray-400 text-sm font-semibold mb-1">TOTAL SENT</h3>
                <p id="total_sent" class="text-3xl font-bold text-emerald-400">0</p>
            </div>
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition"><span class="text-6xl">👤</span></div>
                <h3 class="text-gray-400 text-sm font-semibold mb-1">LIVE ACCOUNTS</h3>
                <p id="live_accs" class="text-3xl font-bold text-blue-400">0/0</p>
            </div>
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition"><span class="text-6xl">🐕</span></div>
                <h3 class="text-gray-400 text-sm font-semibold mb-1">WDT SAVES</h3>
                <p id="wdt_saves" class="text-3xl font-bold text-yellow-400">0</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <!-- Session Management -->
            <div class="glass p-6 rounded-2xl">
                <h2 class="text-lg font-bold mb-4 flex items-center gap-2"><span class="text-emerald-400">🔐</span> Session IDs</h2>
                <div class="flex gap-2 mb-4">
                    <input type="text" id="sess_input" placeholder="Paste session ID here..." class="flex-1 bg-gray-900/50 border border-gray-700 rounded-lg p-3 text-white text-sm focus:outline-none focus:border-emerald-500 transition">
                    <button onclick="addSession()" class="bg-emerald-600 hover:bg-emerald-500 px-5 py-3 rounded-lg text-sm font-bold shadow-lg shadow-emerald-500/20 transition active:scale-95">Add</button>
                </div>
                <div id="session_list" class="space-y-2 max-h-52 overflow-y-auto pr-2">
                    <!-- Sessions load here -->
                </div>
            </div>

            <!-- Config -->
            <div class="glass p-6 rounded-2xl">
                <h2 class="text-lg font-bold mb-4 flex items-center gap-2"><span class="text-blue-400">⚙️</span> Configuration</h2>
                <div class="mb-4">
                    <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">Target Name</label>
                    <input type="text" id="target_input" class="w-full bg-gray-900/50 border border-gray-700 rounded-lg p-3 text-white text-sm focus:outline-none focus:border-blue-500 transition" onchange="saveConfig()">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">GC Link</label>
                    <input type="text" id="gc_input" class="w-full bg-gray-900/50 border border-gray-700 rounded-lg p-3 text-white text-sm focus:outline-none focus:border-blue-500 transition" onchange="saveConfig()">
                </div>
            </div>
        </div>

        <!-- Master Switch -->
        <div class="glass p-6 rounded-2xl flex justify-between items-center mb-8 border border-gray-600/50">
            <div>
                <h2 class="text-xl font-bold text-white">Spam Engine</h2>
                <p class="text-sm text-gray-400">Turn ON to start sending messages</p>
            </div>
            <div class="flex items-center gap-4">
                <span id="engine_status" class="text-sm font-bold text-red-400">STOPPED</span>
                <div class="relative inline-block w-16 mr-2 align-middle select-none transition duration-200 ease-in">
                    <input type="checkbox" name="toggle" id="toggle" class="toggle-checkbox absolute block w-8 h-8 rounded-full bg-white border-4 appearance-none cursor-pointer z-10 transition-transform duration-300" onchange="toggleEngine()"/>
                    <label for="toggle" class="toggle-label block overflow-hidden h-8 rounded-full bg-gray-700 cursor-pointer transition-colors duration-300"></label>
                </div>
            </div>
        </div>

        <!-- Terminal Logs -->
        <div class="glass rounded-2xl border border-gray-800 overflow-hidden">
            <div class="bg-gray-900/80 px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-red-500"></div>
                <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div class="w-3 h-3 rounded-full bg-green-500"></div>
                <span class="ml-2 text-xs font-mono text-gray-400">Live Logs</span>
            </div>
            <div id="logs" class="p-4 h-64 overflow-y-auto font-mono text-xs space-y-1.5 bg-[#0a0f1c]">
                <!-- Logs load here -->
            </div>
        </div>
    </div>

    <script>
        // Initial Data Fetch
        fetch('/api/data').then(r => r.json()).then(data => {
            document.getElementById('target_input').value = data.target;
            document.getElementById('gc_input').value = data.gc_link;
            document.getElementById('toggle').checked = data.running;
            updateUI(data);
        });

        // Real-time Poll
        setInterval(() => {
            fetch('/api/data').then(r => r.json()).then(data => updateUI(data));
        }, 2000);

        function updateUI(data) {
            document.getElementById('total_sent').innerText = data.total_sent;
            document.getElementById('wdt_saves').innerText = data.wdt_saves;
            
            const live = data.sessions.length;
            document.getElementById('live_accs').innerText = `${live}/${live}`;
            
            // Update Engine Status Text
            const statusEl = document.getElementById('engine_status');
            if(data.running) {
                statusEl.innerText = "RUNNING";
                statusEl.className = "text-sm font-bold text-emerald-400";
            } else {
                statusEl.innerText = "STOPPED";
                statusEl.className = "text-sm font-bold text-red-400";
            }
            
            // Sessions
            const sessDiv = document.getElementById('session_list');
            sessDiv.innerHTML = '';
            if(data.sessions.length === 0) {
                sessDiv.innerHTML = '<div class="text-gray-500 text-sm italic text-center py-4">No sessions added yet.</div>';
            }
            data.sessions.forEach(s => {
                sessDiv.innerHTML += `
                    <div class="flex justify-between items-center bg-gray-800/40 p-3 rounded-lg border border-gray-700/50 hover:bg-gray-800/80 transition group">
                        <span class="font-mono text-emerald-400 font-medium">@${s}</span>
                        <button onclick="removeSession('${s}')" class="text-gray-500 hover:text-red-400 bg-gray-700/50 hover:bg-red-500/20 p-2 rounded-md transition" title="Remove Session">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>
                `;
            });
            
            // Logs
            const logDiv = document.getElementById('logs');
            logDiv.innerHTML = '';
            data.logs.forEach(log => {
                let color = "text-gray-300";
                if(log.includes("✅") || log.includes("🔥")) color = "text-emerald-400";
                if(log.includes("⚠️")) color = "text-yellow-400";
                if(log.includes("❌") || log.includes("🚨")) color = "text-red-400";
                if(log.includes("🐕")) color = "text-blue-400";
                logDiv.innerHTML += `<div class="${color} leading-relaxed">${log}</div>`;
            });
        }

        function addSession() {
            const val = document.getElementById('sess_input').value.trim();
            if(!val) return;
            document.getElementById('sess_input').value = 'Authenticating...';
            
            fetch('/api/add_session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: val})
            }).then(r => r.json()).then(res => {
                document.getElementById('sess_input').value = '';
                if(!res.success) alert(res.error);
            });
        }

        function removeSession(username) {
            if(!confirm('Are you sure you want to remove @' + username + '?')) return;
            fetch('/api/remove_session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username})
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
    session.pop('browser_id', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    get_state() # Ensure state exists
    return render_template_string(PANEL_HTML)

@app.route('/api/data')
def get_data():
    if not session.get('logged_in'): return jsonify({})
    st = get_state()
    return jsonify({
        "running": st["running"],
        "total_sent": st["total_sent"],
        "wdt_saves": st["wdt_saves"],
        "target": st["target"],
        "gc_link": st["thread_id"],
        "sessions": [s["username"] for s in st["sessions"]],
        "logs": st["logs"]
    })

@app.route('/api/add_session', methods=['POST'])
def add_session():
    if not session.get('logged_in'): return jsonify({"success": False, "error": "Unauthorized"})
    st = get_state()
    data = request.json
    sid = data.get('session_id', '').strip()
    
    try:
        cl = build_client(sid)
        cl.login_by_sessionid(sid)
        info = cl.account_info()
        
        if any(s["session_id"] == sid for s in st["sessions"]):
            return jsonify({"success": False, "error": "Session already added"})
            
        new_sess = {
            "session_id": sid,
            "username": info.username,
            "client": cl,
            "sent": 0,
            "last_send": time.time(),
            "wdt_saves": 0,
            "cooldown_until": 0
        }
        st["sessions"].append(new_sess)
        add_log(st, f"✅ Added session @{info.username}")
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:100]})

@app.route('/api/remove_session', methods=['POST'])
def remove_session():
    if not session.get('logged_in'): return jsonify({"success": False})
    st = get_state()
    username = request.json.get('username')
    
    st["sessions"] = [s for s in st["sessions"] if s["username"] != username]
    add_log(st, f"🗑️ Removed session @{username}")
    return jsonify({"success": True})

@app.route('/api/save_config', methods=['POST'])
def save_config():
    if not session.get('logged_in'): return jsonify({"success": False})
    st = get_state()
    data = request.json
    st["target"] = data.get('target', '')
    gc_link = data.get('gc_link', '')
    
    m = re.search(r"(\d{15,})", gc_link)
    if m:
        st["thread_id"] = m.group(1)
        add_log(st, f"✅ GC Link set: {st['thread_id']}")
    else:
        st["thread_id"] = ""
        
    return jsonify({"success": True})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    if not session.get('logged_in'): return jsonify({"success": False})
    st = get_state()
    data = request.json
    
    if data.get('running'):
        if not st["sessions"]:
            return jsonify({"success": False, "error": "No sessions added"})
        if not st["target"] or not st["thread_id"]:
            return jsonify({"success": False, "error": "Config missing"})
            
        start_engine(st)
    else:
        st["running"] = False
        add_log(st, "🛑 Spam Engine Stopped")
        
    return jsonify({"success": True})

if __name__ == "__main__":
    print("[+] REXI WEB PANEL BOOTING...")
    print(f"[+] Access Key: {ACCESS_KEY}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
