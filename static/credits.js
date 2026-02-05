// ==========================================
// Update Credit - Frontend Logic
// ==========================================

let isRunning = false;
let pollInterval = null;
let refreshInterval = null;

document.addEventListener('DOMContentLoaded', function () {
    initializePage();
    setupEventListeners();
    startAutoRefresh();
});

// ==========================================
// INITIALIZATION
// ==========================================

async function initializePage() {
    await loadStats();
    await loadTableData();
}

function setupEventListeners() {
    document.getElementById('updateAllBtn').addEventListener('click', handleUpdateAll);
    document.getElementById('stopBtn').addEventListener('click', handleStop);
    document.getElementById('clearConsole').addEventListener('click', clearConsole);
}

// ==========================================
// DATA LOADING
// ==========================================

async function loadStats() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        document.getElementById('totalAccounts').textContent = data.length;

        const withCredits = data.filter(row => {
            const credit = parseFloat(row.remain_credit);
            return !isNaN(credit) && credit > 0;
        }).length;
        document.getElementById('withCredits').textContent = withCredits;
    } catch (error) {
        logToConsole(`Error loading stats: ${error.message}`, 'error');
    }
}

async function loadTableData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        const tbody = document.getElementById('tableBody');

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No accounts found.</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(row => {
            const credit = row.remain_credit ? `$${row.remain_credit}` : '-';
            const creditClass = row.remain_credit && parseFloat(row.remain_credit) > 0 ? 'credit-value' : '';

            return `
                <tr data-email="${escapeHtml(row.email)}">
                    <td>${escapeHtml(row.email)}</td>
                    <td>${escapeHtml(row.full_name || '-')}</td>
                    <td>${escapeHtml(row.card || '-')}</td>
                    <td class="${creditClass}">${credit}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        logToConsole(`Error loading table: ${error.message}`, 'error');
    }
}

function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (!isRunning) {  // Only auto-refresh when not running (to avoid conflicts)
            loadTableData();
        }
    }, 5000);
}

// ==========================================
// ACTION HANDLERS
// ==========================================

async function handleUpdateAll() {
    const btn = document.getElementById('updateAllBtn');
    const stopBtn = document.getElementById('stopBtn');
    const progressSection = document.getElementById('progressSection');
    const summarySection = document.getElementById('summarySection');

    // Update UI state
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Running...';
    stopBtn.classList.remove('hidden');
    progressSection.classList.remove('hidden');
    summarySection.classList.add('hidden');

    isRunning = true;

    logToConsole('Starting credit update for all accounts...', 'info');

    try {
        const response = await fetch('/api/credits/update-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.status === 'started') {
            logToConsole('Update process started. Monitoring progress...', 'info');
            startPolling();
        } else {
            throw new Error(result.message || 'Failed to start update');
        }
    } catch (error) {
        logToConsole(`Error: ${error.message}`, 'error');
        resetUI();
    }
}

async function handleStop() {
    logToConsole('Sending stop request...', 'warning');

    try {
        await fetch('/api/credits/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        logToConsole('Stop request sent. Waiting for current account to finish...', 'warning');
    } catch (error) {
        logToConsole(`Error sending stop request: ${error.message}`, 'error');
    }
}

// ==========================================
// POLLING
// ==========================================

function startPolling() {
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/credits/status');
            const status = await response.json();

            // Update progress
            updateProgress(status);

            // Log new messages
            if (status.messages && status.messages.length > 0) {
                status.messages.forEach(msg => {
                    logToConsole(msg.text, msg.type || 'info');
                });
            }

            // Refresh table data
            await loadTableData();

            // Highlight current row
            if (status.current_email) {
                highlightRow(status.current_email);
            }

            // Check if complete
            if (status.status === 'complete' || status.status === 'stopped') {
                stopPolling();
                showSummary(status);
                resetUI();

                if (status.status === 'complete') {
                    logToConsole('✓ Credit update complete!', 'success');
                } else {
                    logToConsole('⚠ Credit update stopped by user.', 'warning');
                }
            } else if (status.status === 'error') {
                stopPolling();
                resetUI();
                logToConsole(`Error: ${status.message}`, 'error');
            }

        } catch (error) {
            logToConsole(`Status check failed: ${error.message}`, 'warning');
        }
    }, 1500);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    isRunning = false;
}

// ==========================================
// UI UPDATES
// ==========================================

function updateProgress(status) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressCount = document.getElementById('progressCount');
    const currentAccount = document.getElementById('currentAccount');

    const total = status.total || 1;
    const completed = status.completed || 0;
    const percent = Math.round((completed / total) * 100);

    progressBar.style.width = `${percent}%`;
    progressCount.textContent = `${completed}/${total}`;
    progressText.textContent = status.status === 'running' ? 'Processing...' : 'Complete';

    if (status.current_email) {
        currentAccount.textContent = `Current: ${status.current_email}`;
    }
}

function highlightRow(email) {
    // Remove previous highlights
    document.querySelectorAll('tr.processing').forEach(row => {
        row.classList.remove('processing');
    });

    // Add highlight to current row
    const row = document.querySelector(`tr[data-email="${email}"]`);
    if (row) {
        row.classList.add('processing');
    }
}

function showSummary(status) {
    const summarySection = document.getElementById('summarySection');
    const progressSection = document.getElementById('progressSection');

    document.getElementById('successCount').textContent = status.successful || 0;
    document.getElementById('failCount').textContent = status.failed || 0;

    progressSection.classList.add('hidden');
    summarySection.classList.remove('hidden');
}

function resetUI() {
    const btn = document.getElementById('updateAllBtn');
    const stopBtn = document.getElementById('stopBtn');

    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = 'Update Credit for All Accounts';
    stopBtn.classList.add('hidden');

    isRunning = false;

    // Reload stats
    loadStats();
}

// ==========================================
// CONSOLE
// ==========================================

function logToConsole(message, type = 'info') {
    const consoleEl = document.getElementById('consoleOutput');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;

    const timestamp = new Date().toLocaleTimeString();
    line.textContent = `[${timestamp}] ${message}`;

    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function clearConsole() {
    const consoleEl = document.getElementById('consoleOutput');
    consoleEl.innerHTML = '<div class="console-line system">Console cleared.</div>';
}

// ==========================================
// UTILITIES
// ==========================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
