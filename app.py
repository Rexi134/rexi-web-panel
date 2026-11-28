import os, re, time, random, threading, hashlib, uuid
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, ClientError, FeedbackRequired,
    LoginRequired, PleaseWaitFewMinutes, RateLimitError
)

app = Flask(__name__)
app.secret_key = "REXI_SUPER_SECRET"

# ─────────────────────── CONFIG & AUTH ───────────────────────
ACCESS_KEY = "REXI_WEB_PANEL_SECRET"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ─────────────────────── DEFAULT PAYLOAD ───────────────────────
DEFAULT_PAYLOAD = """{e1} █▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓▒░[Rexi God]░▒▓██ ➪ {hater} 𝗖𝗨𝗗𝗔𝗜 𝗦𝗧𝗔𝗥𝗧... █████████████████████████[◈] [◈]  𝗘𝗥𝗥𝗢𝗥 𝟱𝟱 ▂▄▆█[▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░] ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿░░▒▒▒▒▓▓▓▓████▓▓▓▓▒▒▒▒░░➔ 𝘀𝘆𝘀-𝗼𝘃𝗲𝗿𝗿𝗶𝗱𝗲:███████████████████████████████[!] {hater} 𝚂𝙻𝙰𝚅𝙴 𝚁𝙴𝚇𝙸 𝙸𝚂 𝚄𝚁 𝙶𝙾𝙳 **{hater} 𝚏𝚌𝚔 𝚞 𝚋𝚝𝚌𝚑**░░▒▒▒▒▓▓▓▓████▓▓▓▓▒▒▒▒░░ {hater} 𝗧𝗠𝗞𝗖 {e1} ████████████████████████████████▓▒░ {hater} ░▒▓███▓▒░ 𝗦𝗔𝗬 ░▒▓███ █▓▒░ 𝕽ꫀ᥊ɪ 𝗗𝗔𝗗 ░▒▓███▓▒░ thread id: 0x7FFF1C░▒▓██▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█▓█ {e1}"""

FLAG_EMOJIS = ["🎗️", "💀", "🔥", "😈", "⚠️", "☠️", "🩸", "⚡", "🕷️", "💢", "🌀", "💣", "🪓", "❄️", "🤬", "👹", "👺", "😡", "🤡", "👿", "🖤", "❤️‍🔥", "💔", "🗡️", "🔪", "⛓️", "🕸️", "🌑", "🌪️", "🌋", "💥", "☄️", "🌩️"]

# ─────────────────────── STATE ───────────────────────
state = {
    "sessions": {}, 
    "proxy": "http://oqerrmdi:c1849knkbeq0@191.96.254.138:6185", 
    "target": "",
    "gc_link": "",
    "thread_id": "",
    "delay": 10.0,
    "payload": DEFAULT_PAYLOAD,
    "running": False,
    "total_sent": 0,
    "wdt_saves": 0,
    "logs": []
}

def add_log(msg, log_type="OK"):
    timestamp = time.strftime("%H:%M:%S")
    state["logs"].insert(0, {"time": timestamp, "type": log_type, "msg": msg})
    if len(state["logs"]) > 100:
        state["logs"].pop()

# ─────────────────────── DEVICE SPOOFING ──────────────────────
DEVICES = [
    ("Xiaomi", "M2101K6G", "sweet", 31, "12", 440, "1080x2260"),
    ("samsung", "SM-A528B", "a52sxq", 33, "13", 420, "1080x2400"),
    ("OnePlus", "LE2101", "oneplusrt", 31, "12", 480, "1080x2260"),
    ("Google", "Pixel 6", "oriole", 33, "13", 420, "1080x2400"),
]

def build_client(sessionid, proxy=None):
    cl = Client()
    if proxy:
        cl.set_proxy(proxy)
    rng = random.Random(hashlib.sha256(sessionid.encode()).hexdigest())
    m, model, dev, av, ar, dpi, res = rng.choice(DEVICES)
    cl.set_device({"manufacturer": m, "model": model, "device": dev, "android_version": av, "android_release": ar, "dpi": f"{dpi}dpi", "resolution": res})
    cl.set_locale("en_US")
    return cl

# ─────────────────────── WORKER ─────────────────────
def account_worker(uname):
    fail_count = 0
    
    while state["running"]:
        if uname not in state["sessions"]:
            break
            
        s = state["sessions"][uname]
        now = time.time()
        
        if now < s["next_send"]:
            time.sleep(0.5)
            continue
            
        try:
            emoji = random.choice(FLAG_EMOJIS)
            # Send Spam
            msg = state["payload"].replace("{hater}", state["target"]).replace("{e1}", emoji)
            s["client"].direct_send(msg, thread_ids=[int(state["thread_id"])])
            
            state["total_sent"] += 1
            s["sent"] += 1
            s["next_send"] = time.time() + state["delay"]
            
            add_log(f"@{uname} sent payload. Next in {int(state['delay'])}s.", "OK")
            fail_count = 0
            
            # NC Logic (15% chance)
            if random.random() < 0.15: 
                nc_emoji = random.choice(FLAG_EMOJIS)
                nc_title = f"{state['target']} तेरी बहन की चूत || {nc_emoji} ||"
                add_log(f"@{uname} NC Lock Reconnecting...", "ERR")
                try:
                    s["client"].direct_thread_update_title(int(state["thread_id"]), nc_title)
                    add_log(f"@{uname} NC SUCCESS", "OK")
                except Exception:
                    add_log(f"@{uname} NC Failed.", "WARN")
            
        except RateLimitError:
            fail_count += 1
            cooldown = min(60 * fail_count, 600) 
            add_log(f"@{uname} hit Rate Limit. Cooling {cooldown}s.", "WARN")
            s["next_send"] = time.time() + cooldown
        except (PleaseWaitFewMinutes, FeedbackRequired):
            fail_count += 1
            cooldown = min(120 * fail_count, 900)
            add_log(f"@{uname} flagged by IG. Cooling {cooldown}s.", "ERR")
            s["next_send"] = time.time() + cooldown
        except Exception as e:
            fail_count += 1
            if fail_count > 5:
                add_log(f"@{uname} Proxy/Network Failure. Pausing.", "ERR")
                s["next_send"] = time.time() + 30
                fail_count = 0
            time.sleep(2)

    add_log("Spam engine stopped.", "ERR")

# ─────────────────────── FLASK ROUTES ────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('key') == ACCESS_KEY:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template_string(LOGIN_TEMPLATE, error="Invalid Access Key")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/state')
@login_required
def get_state():
    safe_sessions = {k: {"sent": v["sent"], "wdt_saves": v["wdt_saves"]} for k, v in state["sessions"].items()}
    return jsonify({
        "sessions": safe_sessions,
        "proxy": state["proxy"],
        "target": state["target"],
        "gc_link": state["gc_link"],
        "delay": state["delay"],
        "payload": state["payload"],
        "running": state["running"],
        "total_sent": state["total_sent"],
        "wdt_saves": state["wdt_saves"],
        "logs": state["logs"]
    })

@app.route('/api/add_session', methods=['POST'])
@login_required
def add_session():
    sid = request.json.get("session_id", "").strip()
    if not sid: return jsonify({"success": False, "error": "Empty session"})
    
    try:
        cl = build_client(sid, state["proxy"])
        cl.login_by_sessionid(sid)
        info = cl.account_info()
        uname = info.username
        
        if uname in state["sessions"]:
            return jsonify({"success": False, "error": "Session already added"})
            
        state["sessions"][uname] = {"client": cl, "sid": sid, "sent": 0, "wdt_saves": 0, "next_send": 0}
        add_log(f"Added session @{uname}", "OK")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:60]})

@app.route('/api/remove_session', methods=['POST'])
@login_required
def remove_session():
    uname = request.json.get("username")
    if uname in state["sessions"]:
        del state["sessions"][uname]
        add_log(f"Removed session @{uname}", "WARN")
    return jsonify({"success": True})

@app.route('/api/save_config', methods=['POST'])
@login_required
def save_config():
    data = request.json
    state["proxy"] = data.get("proxy", "")
    state["target"] = data.get("target", "")
    state["gc_link"] = data.get("gc_link", "")
    state["delay"] = float(data.get("delay", 10.0))
    state["payload"] = data.get("payload", DEFAULT_PAYLOAD)
    
    m = re.search(r"(\d{15,})", state["gc_link"])
    if m: state["thread_id"] = m.group(1)
    else: state["thread_id"] = ""
    
    if "payload" in data:
        add_log(f"Custom payload updated ({len(state['payload'])} chars)", "OK")
    elif "gc_link" in data and m:
        add_log(f"GC Link set: {state['thread_id']}", "OK")
        
    return jsonify({"success": True})

@app.route('/api/toggle', methods=['POST'])
@login_required
def toggle():
    data = request.json
    
    if data.get("running"):
        if not state["sessions"]: return jsonify({"success": False, "error": "No sessions added"})
        if not state["target"] or not state["thread_id"]: return jsonify({"success": False, "error": "Config missing"})
        
        state["running"] = True
        add_log("Spam Engine Started", "OK")
        
        for uname in state["sessions"].keys():
            threading.Thread(target=account_worker, args=(uname,), daemon=True).start()
    else:
        state["running"] = False
        add_log("Spam Engine Stopped", "ERR")
        
    return jsonify({"success": True})

@app.route('/api/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    state["logs"] = []
    return jsonify({"success": True})

# ─────────────────────── LOGIN TEMPLATE ───────────────────────
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rexi Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background-color: #f8fafc; } </style>
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-2xl shadow-xl border border-slate-200 w-96">
        <div class="flex justify-center mb-6">
            <div class="w-12 h-12 bg-slate-900 rounded-xl flex items-center justify-center text-white text-2xl shadow-lg">⚡</div>
        </div>
        <h1 class="text-xl font-bold text-center text-slate-900 mb-2">Restricted Access</h1>
        <p class="text-xs text-center text-slate-500 mb-6">Enter the secret key to access the panel.</p>
        
        {% if error %}
        <div class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4 text-center border border-red-200">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <input type="password" name="key" placeholder="Enter Access Key" class="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-900 mb-4 focus:outline-none focus:border-slate-900" required>
            <button type="submit" class="w-full bg-slate-900 text-white font-bold py-3 rounded-lg hover:bg-slate-800 transition">Verify & Login</button>
        </form>
    </div>
</body>
</html>
"""

# ─────────────────────── DASHBOARD TEMPLATE ───────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rexi Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #0f172a; }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); border: 1px solid #e2e8f0; }
        .input-field { width: 100%; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px 16px; color: #0f172a; font-size: 14px; transition: all 0.2s; }
        .input-field:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        .btn-primary { background: #0f172a; color: white; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 14px; transition: background 0.2s; }
        .btn-primary:hover { background: #1e293b; }
        .badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }
        .badge-ok { background: #dcfce7; color: #166534; }
        .badge-err { background: #fee2e2; color: #991b1b; }
        .badge-warn { background: #fef3c7; color: #92400e; }
        .switch { position: relative; display: inline-block; width: 60px; height: 34px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .4s; border-radius: 34px; }
        .slider:before { position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #10b981; }
        input:checked + .slider:before { transform: translateX(26px); }
    </style>
</head>
<body class="p-4 md:p-8 min-h-screen">
    <div class="max-w-3xl mx-auto space-y-6">

        <!-- Top Nav -->
        <div class="flex justify-between items-center mb-2">
            <div class="text-lg font-bold flex items-center gap-2">
                Rexi Panel <span class="text-[10px] bg-slate-900 text-white px-2 py-0.5 rounded-full">v2.0</span>
            </div>
            <a href="/logout" class="text-xs font-bold text-red-500 hover:text-red-700 bg-red-50 px-3 py-1.5 rounded-lg transition">Logout</a>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="card p-5">
                <div class="flex justify-between items-center text-slate-400 text-xs font-bold mb-1">
                    <span>TOTAL DISPATCHED</span><span>📤</span>
                </div>
                <div id="stat_total" class="text-3xl font-black text-slate-900">0</div>
                <div class="text-xs text-slate-400 mt-1">Payloads this session</div>
            </div>
            <div class="card p-5">
                <div class="flex justify-between items-center text-slate-400 text-xs font-bold mb-1">
                    <span>LIVE ACCOUNTS</span><span>👤</span>
                </div>
                <div id="stat_live" class="text-3xl font-black text-slate-900">0/0</div>
                <div class="text-xs text-slate-400 mt-1">Active sessions</div>
            </div>
            <div class="card p-5">
                <div class="flex justify-between items-center text-slate-400 text-xs font-bold mb-1">
                    <span>WATCHDOG SAVES</span><span>🛡️</span>
                </div>
                <div id="stat_wdt" class="text-3xl font-black text-slate-900">0</div>
                <div class="text-xs text-slate-400 mt-1">Auto-recovered threads</div>
            </div>
            <div class="card p-5">
                <div class="flex justify-between items-center text-slate-400 text-xs font-bold mb-1">
                    <span>DELAY</span><span>⏱️</span>
                </div>
                <div id="stat_delay" class="text-3xl font-black text-slate-900">10S</div>
                <div class="text-xs text-slate-400 mt-1">Per-account interval</div>
            </div>
        </div>

        <!-- Sessions -->
        <div class="card p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">🔒</div>
                <div>
                    <h2 class="font-bold text-slate-900">Sessions</h2>
                    <p class="text-xs text-slate-500">Instagram session IDs</p>
                </div>
            </div>
            <div class="flex gap-2 mb-4">
                <input type="text" id="session_input" class="input-field" placeholder="Paste sessionid...">
                <button onclick="addSession()" class="btn-primary">Add</button>
            </div>
            <div id="session_list" class="space-y-2"></div>
        </div>

        <!-- Configuration -->
        <div class="card p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">⚙️</div>
                <div>
                    <h2 class="font-bold text-slate-900">Configuration</h2>
                    <p class="text-xs text-slate-500">Auto-saves on change</p>
                </div>
            </div>
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1">RESIDENTIAL PROXY URL</label>
                    <input type="text" id="cfg_proxy" class="input-field" placeholder="http://user:pass@ip:port" onchange="saveConfig()">
                </div>
                <div>
                    <div class="flex justify-between items-center mb-1">
                        <label class="block text-xs font-bold text-slate-500">TARGET NAME</label>
                        <span class="text-xs font-mono text-slate-400">{HATER}</span>
                    </div>
                    <input type="text" id="cfg_target" class="input-field" placeholder="TEST" onchange="saveConfig()">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1">THREAD / GROUP CHAT LINK</label>
                    <input type="text" id="cfg_gc" class="input-field" placeholder="https://www.instagram.com/direct/t/..." onchange="saveConfig()">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1">MESSAGE DELAY (SECONDS)</label>
                    <input type="number" id="cfg_delay" class="input-field" min="1" onchange="saveConfig()">
                </div>
            </div>
        </div>

        <!-- Payload Studio -->
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h2 class="font-bold text-slate-900 flex items-center gap-2">
                        <span class="text-slate-400 text-lg">&lt;&gt;</span> Payload Studio
                    </h2>
                    <p class="text-xs text-slate-500">Edit or upload a .txt payload</p>
                </div>
                <button class="px-3 py-1.5 bg-slate-100 rounded-lg text-xs font-semibold hover:bg-slate-200">⬆️ Upload</button>
            </div>
            
            <div class="flex gap-2 items-center mb-2 text-xs text-slate-500">
                <span>Variables:</span>
                <span class="px-2 py-1 border rounded-md bg-white font-mono">{hater}</span>
                <span class="px-2 py-1 border rounded-md bg-white font-mono">{e1}</span>
                <button onclick="previewPayload()" class="ml-auto px-2 py-1 border rounded-md bg-white hover:bg-slate-50">Preview</button>
                <span id="char_count" class="ml-2 font-mono">0 chars</span>
            </div>

            <textarea id="cfg_payload" class="input-field font-mono text-xs h-48 resize-y mb-4" oninput="updateCharCount()" onchange="saveConfig()"></textarea>

            <div class="flex justify-between items-center">
                <button onclick="resetPayload()" class="px-4 py-2 border rounded-lg text-sm font-semibold hover:bg-slate-50">Reset Default</button>
                <button onclick="saveConfig()" class="btn-primary">Save Payload</button>
            </div>
        </div>

        <!-- Dispatch Engine -->
        <div class="card p-6 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 text-xl">⚡</div>
                <div>
                    <h2 class="font-bold text-slate-900">Dispatch Engine</h2>
                    <p class="text-xs text-slate-500">Threaded sender with 35s watchdog</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <span id="engine_status" class="text-xs font-bold text-slate-400 tracking-wider">STANDBY</span>
                <label class="switch">
                    <input type="checkbox" id="engine_toggle" onchange="toggleEngine()">
                    <span class="slider"></span>
                </label>
            </div>
        </div>

        <!-- Live Logs -->
        <div class="card p-0 overflow-hidden">
            <div class="p-4 flex justify-between items-center border-b border-slate-100">
                <div class="flex items-center gap-2 font-bold text-slate-900">
                    <div class="w-2 h-2 rounded-full bg-emerald-400"></div> Live Logs
                </div>
                <div class="flex gap-2 text-xs font-semibold">
                    <button onclick="setFilter('All')" class="px-3 py-1 bg-slate-100 rounded-md" id="f_all">All</button>
                    <button onclick="setFilter('OK')" class="px-3 py-1 text-slate-400 hover:text-slate-700" id="f_OK">OK</button>
                    <button onclick="setFilter('WARN')" class="px-3 py-1 text-slate-400 hover:text-slate-700" id="f_WARN">Warn</button>
                    <button onclick="setFilter('ERR')" class="px-3 py-1 text-slate-400 hover:text-slate-700" id="f_ERR">Err</button>
                    <div class="w-px bg-slate-200 mx-1"></div>
                    <button onclick="copyLogs()" class="px-3 py-1 border border-slate-200 rounded-md hover:bg-slate-50">Copy</button>
                    <button onclick="clearLogs()" class="px-3 py-1 border border-slate-200 rounded-md hover:bg-slate-50">Clear</button>
                </div>
            </div>
            <div id="log_container" class="p-4 space-y-2 h-64 overflow-y-auto bg-slate-50 text-xs font-mono"></div>
        </div>

        <div class="text-center text-xs text-slate-400 mt-8 pb-4">
            © 2026 Rexi. <b>Anti-Ban</b> Terms
        </div>
    </div>

    <script>
        let allLogs = [];
        let currentFilter = 'All';
        const DEFAULT_PAYLOAD = `""" + DEFAULT_PAYLOAD.replace('`', '\\`') + """`;

        function updateUI(data) {
            document.getElementById('stat_total').innerText = data.total_sent;
            document.getElementById('stat_wdt').innerText = data.wdt_saves;
            document.getElementById('stat_delay').innerText = data.delay + 's';
            
            const live = Object.keys(data.sessions).length;
            document.getElementById('stat_live').innerText = `${live}/${live}`;
            
            document.getElementById('engine_toggle').checked = data.running;
            const st = document.getElementById('engine_status');
            if(data.running) {
                st.innerText = "ACTIVE"; st.className = "text-xs font-bold text-emerald-500 tracking-wider";
            } else {
                st.innerText = "STANDBY"; st.className = "text-xs font-bold text-slate-400 tracking-wider";
            }
            
            if(document.activeElement !== document.getElementById('cfg_proxy')) document.getElementById('cfg_proxy').value = data.proxy;
            if(document.activeElement !== document.getElementById('cfg_target')) document.getElementById('cfg_target').value = data.target;
            if(document.activeElement !== document.getElementById('cfg_gc')) document.getElementById('cfg_gc').value = data.gc_link;
            if(document.activeElement !== document.getElementById('cfg_delay')) document.getElementById('cfg_delay').value = data.delay;
            if(document.activeElement !== document.getElementById('cfg_payload')) {
                document.getElementById('cfg_payload').value = data.payload;
                updateCharCount();
            }
            
            const sList = document.getElementById('session_list');
            sList.innerHTML = '';
            for(const [uname, sData] of Object.entries(data.sessions)) {
                sList.innerHTML += `
                    <div class="flex items-center justify-between p-3 border border-slate-200 rounded-xl bg-white shadow-sm">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 bg-emerald-100 text-emerald-700 font-bold rounded-lg flex items-center justify-center text-xs">RE</div>
                            <div>
                                <div class="font-bold text-sm text-slate-800">@${uname}</div>
                                <div class="text-xs text-slate-500">${sData.sent} sent • ${sData.wdt_saves} saves</div>
                            </div>
                        </div>
                        <button onclick="removeSession('${uname}')" class="px-3 py-1.5 bg-red-50 text-red-600 text-xs font-bold rounded-lg hover:bg-red-100 transition">Remove</button>
                    </div>`;
            }
            
            allLogs = data.logs;
            renderLogs();
        }

        function renderLogs() {
            const container = document.getElementById('log_container');
            container.innerHTML = '';
            allLogs.forEach(log => {
                if(currentFilter !== 'All' && log.type !== currentFilter) return;
                
                let badgeClass = "badge-ok";
                if(log.type === 'ERR') badgeClass = "badge-err";
                if(log.type === 'WARN') badgeClass = "badge-warn";
                
                let icon = log.type === 'ERR' ? '🔴' : (log.type === 'WARN' ? '⚠️' : '📨');
                
                container.innerHTML += `
                    <div class="flex gap-3 items-start">
                        <span class="text-slate-400">${log.time}</span>
                        <span class="badge ${badgeClass}">${log.type}</span>
                        <span class="text-slate-700">${icon} ${log.msg}</span>
                    </div>
                `;
            });
        }

        function setFilter(f) {
            currentFilter = f;
            ['All', 'OK', 'WARN', 'ERR'].forEach(x => {
                const btn = document.getElementById('f_' + x);
                if(x === f) btn.className = "px-3 py-1 bg-slate-100 rounded-md";
                else btn.className = "px-3 py-1 text-slate-400 hover:text-slate-700";
            });
            renderLogs();
        }

        function updateCharCount() {
            const len = document.getElementById('cfg_payload').value.length;
            document.getElementById('char_count').innerText = len + " chars";
        }

        function saveConfig() {
            const proxy = document.getElementById('cfg_proxy').value;
            const target = document.getElementById('cfg_target').value;
            const gc = document.getElementById('cfg_gc').value;
            const delay = document.getElementById('cfg_delay').value;
            const payload = document.getElementById('cfg_payload').value;
            
            fetch('/api/save_config', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({proxy, target, gc_link: gc, delay, payload})
            });
        }

        function addSession() {
            const val = document.getElementById('session_input').value.trim();
            if(!val) return;
            document.getElementById('session_input').value = '...';
            fetch('/api/add_session', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: val})
            }).then(r => r.json()).then(res => {
                document.getElementById('session_input').value = '';
                if(!res.success) alert(res.error);
            });
        }

        function removeSession(username) {
            fetch('/api/remove_session', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username})
            });
        }

        function toggleEngine() {
            const isRunning = document.getElementById('engine_toggle').checked;
            fetch('/api/toggle', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({running: isRunning})
            }).then(r => r.json()).then(res => {
                if(!res.success) {
                    alert(res.error);
                    document.getElementById('engine_toggle').checked = !isRunning;
                }
            });
        }

        function resetPayload() {
            if(!confirm('Reset payload to default?')) return;
            document.getElementById('cfg_payload').value = DEFAULT_PAYLOAD;
            updateCharCount();
            saveConfig();
        }

        function previewPayload() {
            const text = document.getElementById('cfg_payload').value;
            const target = document.getElementById('cfg_target').value || '{hater}';
            const preview = text.replace(/{hater}/g, target).replace(/{e1}/g, '🎗️');
            alert(preview);
        }

        function copyLogs() {
            const text = allLogs.map(l => `[${l.time}] [${l.type}] ${l.msg}`).join('\\n');
            navigator.clipboard.writeText(text);
            alert('Logs copied!');
        }

        function clearLogs() {
            fetch('/api/clear_logs', {method: 'POST'}).then(() => { allLogs = []; renderLogs(); });
        }

        fetch('/api/state').then(r => r.json()).then(updateUI);
        setInterval(() => {
            fetch('/api/state').then(r => r.json()).then(updateUI);
        }, 1500);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("[+] REXI PANEL BOOTING...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
