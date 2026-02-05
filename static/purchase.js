// ==========================================
// Make Purchase - Frontend Logic
// ==========================================

document.addEventListener('DOMContentLoaded', function () {
    loadAccounts();
    loadMerchandise();
    startStatusPolling();

    // Event Listeners
    document.getElementById('refreshAccounts').addEventListener('click', loadAccounts);
    document.getElementById('addMerchBtn').addEventListener('click', addNewMerchandise);

    // Toast notification
    window.showToast = function (message) {
        const toast = document.getElementById('toast');
        const text = toast.querySelector('.toast-text');
        text.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    };
});

// ==========================================
// ACCOUNTS HANDLING
// ==========================================

async function loadAccounts() {
    const list = document.getElementById('accountList');
    const tableBody = document.getElementById('tableBody');
    const eligibleCountBadge = document.getElementById('eligibleCount');
    const totalAccountsBadge = document.getElementById('totalAccounts');

    list.innerHTML = '<div class="loading">Loading accounts...</div>';

    try {
        const response = await fetch('/api/purchase/accounts');
        const data = await response.json();

        // Update Table
        updateTable(data.all_accounts);
        totalAccountsBadge.textContent = `${data.all_accounts.length} accounts`;

        // Update Eligible List
        list.innerHTML = '';
        if (data.eligible_accounts.length === 0) {
            list.innerHTML = '<div class="empty-state">No eligible accounts found (Need card assigned)</div>';
        } else {
            data.eligible_accounts.forEach(account => {
                const item = document.createElement('div');
                item.className = 'account-item';
                item.innerHTML = `
                    <div class="account-info">
                        <div class="account-email">${account.email}</div>
                        <div class="account-balance">Credit: $${account.remain_credit}</div>
                    </div>
                    <div class="account-actions">
                        <button class="btn-open" onclick="startPurchaseSession('${account.email}')">Marketplace</button>
                    </div>
                `;
                list.appendChild(item);
            });
        }
        eligibleCountBadge.textContent = `${data.eligible_accounts.length} eligible`;

    } catch (error) {
        console.error('Error loading accounts:', error);
        list.innerHTML = '<div class="error">Error loading accounts</div>';
    }
}

function updateTable(accounts) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    accounts.forEach(acc => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${acc.email}</td>
            <td>${acc.card || '-'}</td>
            <td>${acc.remain_credit ? '$' + acc.remain_credit : '-'}</td>
            <td>${acc.full_name || '-'}</td>
            <td>${acc.full_address || '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// MERCHANDISE HANDLING
// ==========================================

async function loadMerchandise() {
    const list = document.getElementById('merchandiseList');
    const badge = document.getElementById('merchCount');

    list.innerHTML = '<div class="loading">Loading merchandise...</div>';

    try {
        const response = await fetch('/api/merchandise');
        const data = await response.json();

        list.innerHTML = '';
        if (data.merchandise.length === 0) {
            list.innerHTML = '<div class="empty-state">No merchandise found</div>';
        } else {
            data.merchandise.forEach(item => {
                const div = document.createElement('div');
                div.className = 'merch-item';
                div.onclick = () => copyToClipboard(item.url);
                div.innerHTML = `
                    <div class="merch-name">${item.name}</div>
                    <div class="merch-copy">Copy URL</div>
                `;
                list.appendChild(div);
            });
        }
        badge.textContent = `${data.merchandise.length} items`;

    } catch (error) {
        console.error('Error loading merchandise:', error);
        list.innerHTML = '<div class="error">Error loading merchandise</div>';
    }
}

async function addNewMerchandise() {
    const nameInput = document.getElementById('newMerchName');
    const urlInput = document.getElementById('newMerchUrl');
    const btn = document.getElementById('addMerchBtn');

    const name = nameInput.value.trim();
    const url = urlInput.value.trim();

    if (!name || !url) {
        alert('Please enter both name and URL');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Adding...';

    try {
        const response = await fetch('/api/merchandise/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url })
        });

        const result = await response.json();

        if (result.status === 'success') {
            nameInput.value = '';
            urlInput.value = '';
            loadMerchandise(); // Reload list
            showToast('Merchandise added!');
        } else {
            alert('Error: ' + result.message);
        }

    } catch (error) {
        console.error('Error adding merchandise:', error);
        alert('Failed to add merchandise');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Add';
    }
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('URL Copied!');
    } catch (err) {
        console.error('Failed to copy:', err);
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('URL Copied!');
    }
}

// ==========================================
// SESSION HANDLING
// ==========================================

async function startPurchaseSession(email) {
    if (!confirm(`Start purchase session for ${email}? This will open a browser window.`)) {
        return;
    }

    try {
        const response = await fetch('/api/purchase/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const result = await response.json();
        if (result.status === 'success') {
            showToast('Browser opening...');
            updateSessionsList(); // Refresh immediately
        } else {
            alert('Error: ' + result.message);
        }

    } catch (error) {
        console.error('Error starting session:', error);
        alert('Failed to start session');
    }
}

async function stopSession(email) {
    if (!confirm(`Close session for ${email}?`)) {
        return;
    }

    try {
        const response = await fetch('/api/purchase/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const result = await response.json();
        if (result.status === 'success') {
            showToast('Session closed');
            updateSessionsList();
        }
    } catch (error) {
        console.error('Error stopping session:', error);
    }
}

// ==========================================
// POLLING
// ==========================================

function startStatusPolling() {
    updateSessionsList();
    setInterval(updateSessionsList, 5000); // Poll every 5 seconds
}

async function updateSessionsList() {
    const list = document.getElementById('sessionList');
    const badge = document.getElementById('sessionCount');

    try {
        const response = await fetch('/api/purchase/sessions');
        const data = await response.json();

        list.innerHTML = '';
        if (data.sessions.length === 0) {
            list.innerHTML = '<div class="empty-state">No active sessions. Select an account to start.</div>';
            badge.textContent = '0 active';
        } else {
            data.sessions.forEach(session => {
                const card = document.createElement('div');
                card.className = 'session-card';
                card.innerHTML = `
                    <div class="session-header">
                        <div class="session-email">${session.email}</div>
                        <div class="session-status ${session.status === 'ready' ? 'active' : 'loading'}">
                            ${session.status === 'ready' ? 'Ready for Purchase' : 'Initializing...'}
                        </div>
                    </div>
                    <div class="session-actions">
                        <button class="btn-close" onclick="stopSession('${session.email}')">Close Session</button>
                    </div>
                `;
                list.appendChild(card);
            });
            badge.textContent = `${data.sessions.length} active`;
        }

    } catch (error) {
        console.error('Error polling sessions:', error);
    }
}
