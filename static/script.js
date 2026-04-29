let currentClient = null;
let clientsData = [];

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        const page = item.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`${page}-page`).classList.add('active');
        document.getElementById('page-title').innerText = item.querySelector('span:last-child').innerText;
        
        if (page === 'clients') loadClients();
        if (page === 'activities') loadActivities();
    });
});

function refreshAll() {
    loadStats();
    if (document.getElementById('clients-page').classList.contains('active')) loadClients();
    if (document.getElementById('activities-page').classList.contains('active')) loadActivities();
    loadRecentActivities();
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('total-clients').innerText = stats.total_clients;
        document.getElementById('online-clients').innerText = stats.online_clients;
        document.getElementById('pending-commands').innerText = stats.pending_commands;
        document.getElementById('executed-commands').innerText = stats.executed_commands;
    } catch(e) { console.error(e); }
}

async function loadClients() {
    try {
        const res = await fetch('/api/clients');
        const clients = await res.json();
        clientsData = clients;
        renderClients(clients);
    } catch(e) { console.error(e); }
}

function renderClients(clients) {
    const container = document.getElementById('clients-grid');
    if (!clients.length) {
        container.innerHTML = '<div style="text-align:center;padding:40px;">Aucun client pour le moment</div>';
        return;
    }
    container.innerHTML = clients.map(client => `
        <div class="client-card ${client.online ? 'online' : 'offline'}">
            <div class="client-header">
                <div class="client-name">${escapeHtml(client.computer_name || client.machine_id)}</div>
                <div class="client-status ${client.online ? 'online' : 'offline'}">${client.online ? '🟢 En ligne' : '⚫ Hors ligne'}</div>
            </div>
            <div class="client-details">
                <p>👤 ${escapeHtml(client.username || '?')}</p>
                <p>💻 ${escapeHtml(client.windows_version || '?')}</p>
                <p>🌐 ${escapeHtml(client.ip || '?')}</p>
                <p>📅 Dernière vue: ${formatDate(client.last_seen)}</p>
            </div>
            <div class="client-actions">
                <button class="btn-small" onclick="openCommandModal('${client.machine_id}', '${escapeHtml(client.computer_name || client.machine_id)}')">⚡ Commande</button>
                <button class="btn-small" onclick="viewClientHistory('${client.machine_id}')">📜 Historique</button>
            </div>
        </div>
    `).join('');
}

function filterClients() {
    const search = document.getElementById('client-search').value.toLowerCase();
    const filtered = clientsData.filter(c => 
        (c.computer_name && c.computer_name.toLowerCase().includes(search)) ||
        (c.username && c.username.toLowerCase().includes(search)) ||
        (c.ip && c.ip.includes(search))
    );
    renderClients(filtered);
}

function formatDate(dateStr) {
    if (!dateStr) return 'Jamais';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000 / 60);
        if (diff < 1) return 'À l\'instant';
        if (diff < 60) return `Il y a ${diff} min`;
        if (diff < 1440) return `Il y a ${Math.floor(diff/60)}h`;
        return date.toLocaleDateString();
    } catch(e) { return dateStr; }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function openCommandModal(machineId, clientName) {
    currentClient = machineId;
    document.getElementById('modal-client-name').innerText = clientName;
    document.getElementById('command-modal').style.display = 'block';
    document.getElementById('command-params-group').style.display = 'none';
    document.getElementById('command-params').value = '';
}

document.getElementById('command-type').addEventListener('change', function() {
    const paramsGroup = document.getElementById('command-params-group');
    if (this.value === 'execute_ps' || this.value === 'execute_cmd') {
        paramsGroup.style.display = 'block';
        if (this.value === 'execute_ps') {
            document.getElementById('command-params').value = 'Get-Process | Select-Object -First 10';
        } else {
            document.getElementById('command-params').value = 'dir';
        }
    } else {
        paramsGroup.style.display = 'none';
    }
});

async function executeCommand() {
    const commandType = document.getElementById('command-type').value;
    let params = {};
    
    if (commandType === 'execute_ps' || commandType === 'execute_cmd') {
        const cmd = document.getElementById('command-params').value;
        if (cmd) params = { command: cmd };
    } else if (commandType === 'kill_process') {
        const pid = prompt('Entrez le PID du processus à tuer:');
        if (pid) params = { pid: parseInt(pid) };
    }
    
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                machine_id: currentClient,
                command_type: commandType,
                params: params
            })
        });
        const data = await res.json();
        if (data.status === 'command queued') {
            alert(`Commande envoyée ! ID: ${data.command_id}`);
            closeModal();
            // Attendre et récupérer le résultat
            waitForResult(data.command_id);
        } else {
            alert('Erreur: ' + (data.error || 'Inconnue'));
        }
    } catch(e) {
        alert('Erreur: ' + e.message);
    }
}

async function waitForResult(commandId, attempts = 0) {
    if (attempts > 30) {
        alert('Timeout - Pas de réponse du client');
        return;
    }
    try {
        const res = await fetch(`/api/command_result/${commandId}`);
        const data = await res.json();
        if (data.status === 'executed') {
            showResult(data.result);
        } else {
            setTimeout(() => waitForResult(commandId, attempts + 1), 2000);
        }
    } catch(e) {
        setTimeout(() => waitForResult(commandId, attempts + 1), 2000);
    }
}

function showResult(result) {
    const content = document.getElementById('result-content');
    if (typeof result === 'string') {
        content.innerText = result;
    } else {
        content.innerText = JSON.stringify(result, null, 2);
    }
    document.getElementById('result-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('command-modal').style.display = 'none';
}

function closeResultModal() {
    document.getElementById('result-modal').style.display = 'none';
}

async function viewClientHistory(machineId) {
    try {
        const res = await fetch(`/api/commands/history/${machineId}`);
        const commands = await res.json();
        const client = clientsData.find(c => c.machine_id === machineId);
        const clientName = client ? (client.computer_name || machineId) : machineId;
        if (!commands.length) {
            alert(`Aucune commande historique pour ${clientName}`);
            return;
        }
        let text = `Historique des commandes - ${clientName}\n${'='.repeat(50)}\n\n`;
        for (const cmd of commands) {
            text += `ID: ${cmd.id}\n`;
            text += `Type: ${cmd.command_type}\n`;
            text += `Status: ${cmd.status}\n`;
            text += `Créée: ${cmd.created_at}\n`;
            if (cmd.executed_at) text += `Exécutée: ${cmd.executed_at}\n`;
            if (cmd.result) text += `Résultat: ${JSON.stringify(cmd.result, null, 2)}\n`;
            text += `${'-'.repeat(40)}\n\n`;
        }
        const content = document.getElementById('result-content');
        content.innerText = text;
        document.getElementById('result-modal').style.display = 'block';
    } catch(e) {
        alert('Erreur: ' + e.message);
    }
}

async function loadRecentActivities() {
    try {
        const res = await fetch('/api/activities');
        const activities = await res.json();
        const container = document.getElementById('recent-activities');
        if (!activities.length) {
            container.innerHTML = '<div class="activity-item">Aucune activité</div>';
            return;
        }
        container.innerHTML = activities.slice(0, 10).map(act => `
            <div class="activity-item">
                <div class="activity-icon">${getActivityIcon(act.action)}</div>
                <div class="activity-content">
                    <div class="activity-action">${escapeHtml(act.action)}</div>
                    ${act.details ? `<div class="activity-details">${escapeHtml(act.details)}</div>` : ''}
                </div>
                <div class="activity-time">${formatDate(act.timestamp)}</div>
            </div>
        `).join('');
    } catch(e) { console.error(e); }
}

async function loadActivities() {
    try {
        const res = await fetch('/api/activities');
        const activities = await res.json();
        const container = document.getElementById('activities-full');
        if (!activities.length) {
            container.innerHTML = '<div class="activity-item">Aucune activité</div>';
            return;
        }
        container.innerHTML = activities.map(act => `
            <div class="activity-item">
                <div class="activity-icon">${getActivityIcon(act.action)}</div>
                <div class="activity-content">
                    <div class="activity-action">${escapeHtml(act.action)}</div>
                    ${act.machine_id ? `<div class="activity-details">Machine: ${escapeHtml(act.machine_id)}</div>` : ''}
                    ${act.details ? `<div class="activity-details">${escapeHtml(act.details)}</div>` : ''}
                </div>
                <div class="activity-time">${formatDate(act.timestamp)}</div>
            </div>
        `).join('');
    } catch(e) { console.error(e); }
}

function getActivityIcon(action) {
    const icons = {
        'heartbeat': '💓',
        'send_command': '⚡',
        'command_result': '✅',
        'login': '🔐',
        'logout': '🚪'
    };
    return icons[action] || '📌';
}

// Fermer modals en cliquant en dehors
window.onclick = function(event) {
    const modal = document.getElementById('command-modal');
    const resultModal = document.getElementById('result-modal');
    if (event.target === modal) closeModal();
    if (event.target === resultModal) closeResultModal();
}

// Initialisation
loadStats();
loadRecentActivities();
setInterval(() => {
    loadStats();
    if (document.getElementById('clients-page').classList.contains('active')) loadClients();
}, 10000);