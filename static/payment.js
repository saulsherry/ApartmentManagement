// ==========================================
// Update Payment - Frontend Logic
// ==========================================

let currentAccount = null;
let browserSessionActive = false;
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
    updateInstructionStep(1);
}

function setupEventListeners() {
    document.getElementById('addPaymentBtn').addEventListener('click', handleAddPayment);
    document.getElementById('skipAccountBtn').addEventListener('click', handleSkipAccount);
    document.getElementById('setAliasBtn').addEventListener('click', handleSetAlias);
    document.getElementById('clearConsole').addEventListener('click', clearConsole);

    // Enable Set Alias button when input has value
    document.getElementById('cardAlias').addEventListener('input', function () {
        document.getElementById('setAliasBtn').disabled = !this.value.trim();
    });
}

// ==========================================
// DATA LOADING
// ==========================================

async function loadStats() {
    try {
        const response = await fetch('/api/payment/stats');
        const stats = await response.json();

        document.getElementById('totalAccounts').textContent = stats.total;
        document.getElementById('noPaymentCount').textContent = stats.no_payment;

        if (stats.next_account) {
            currentAccount = stats.next_account;
            document.getElementById('currentEmail').textContent = stats.next_account.email;
            document.getElementById('addPaymentBtn').disabled = false;
        } else {
            document.getElementById('currentEmail').textContent = 'All accounts have payment!';
            document.getElementById('addPaymentBtn').disabled = true;
            logToConsole('✓ All accounts already have payment methods set.', 'success');
        }
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
            const hasCard = row.card && row.card.trim() !== '';
            const isCurrent = currentAccount && row.email === currentAccount.email;

            let rowClass = '';
            if (isCurrent) rowClass = 'current-row';
            else if (!hasCard) rowClass = 'no-payment';

            return `
                <tr class="${rowClass}">
                    <td>${escapeHtml(row.email)}</td>
                    <td>${escapeHtml(row.full_name || '-')}</td>
                    <td>${hasCard ? escapeHtml(row.card) : '(none)'}</td>
                    <td>${row.remain_credit ? '$' + row.remain_credit : '-'}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        logToConsole(`Error loading table: ${error.message}`, 'error');
    }
}

function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        loadTableData();
    }, 3000);
}

// ==========================================
// ACTION HANDLERS
// ==========================================

async function handleAddPayment() {
    if (!currentAccount) {
        logToConsole('No account selected.', 'warning');
        return;
    }

    const btn = document.getElementById('addPaymentBtn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Opening Browser...';

    logToConsole(`Starting login for ${currentAccount.email}...`, 'info');
    updateInstructionStep(1, true);

    try {
        const response = await fetch('/api/payment/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentAccount.email })
        });

        const result = await response.json();

        if (result.status === 'success') {
            browserSessionActive = true;
            logToConsole('✓ Browser opened and logged in successfully!', 'success');
            logToConsole('→ Please manually enter credit card details on the website.', 'info');

            updateInstructionStep(2, true);

            // Enable skip and alias input
            document.getElementById('skipAccountBtn').disabled = false;
            document.getElementById('cardAlias').disabled = false;
            document.getElementById('cardAlias').focus();

            btn.querySelector('.btn-text').textContent = 'Browser Open';
        } else {
            throw new Error(result.message || 'Failed to start browser session');
        }
    } catch (error) {
        logToConsole(`Error: ${error.message}`, 'error');
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = 'Add Payment';
    }
}

async function handleSkipAccount() {
    if (!currentAccount) return;

    const skipBtn = document.getElementById('skipAccountBtn');
    skipBtn.disabled = true;

    logToConsole(`Skipping ${currentAccount.email}...`, 'warning');

    try {
        // Call the skip API endpoint to close browser if open
        const response = await fetch('/api/payment/skip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentAccount.email })
        });

        const result = await response.json();

        if (result.status === 'success') {
            logToConsole('✓ Account skipped', 'success');
        }
    } catch (error) {
        logToConsole(`Error skipping: ${error.message}`, 'error');
    }

    // Reset UI state
    resetUIState();

    // Reload to get next account
    await loadStats();
    await loadTableData();

    logToConsole('Ready for next account.', 'info');
    updateInstructionStep(1);

    skipBtn.disabled = false;
}

async function handleSetAlias() {
    const alias = document.getElementById('cardAlias').value.trim();

    if (!alias) {
        logToConsole('Please enter a card alias first.', 'warning');
        return;
    }

    if (!currentAccount) {
        logToConsole('No account selected.', 'error');
        return;
    }

    const btn = document.getElementById('setAliasBtn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Saving...';

    logToConsole(`Setting card alias "${alias}" for ${currentAccount.email}...`, 'info');
    updateInstructionStep(4, true);

    try {
        const response = await fetch('/api/payment/set-alias', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: currentAccount.email,
                card_alias: alias
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            logToConsole(`✓ Card alias set successfully!`, 'success');
            markAllStepsComplete();

            // Reset for next account
            resetUIState();
            document.getElementById('cardAlias').value = '';

            // Reload data
            await loadStats();
            await loadTableData();

            logToConsole('Ready for next account.', 'info');
            updateInstructionStep(1);
        } else {
            throw new Error(result.message || 'Failed to set alias');
        }
    } catch (error) {
        logToConsole(`Error: ${error.message}`, 'error');
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = 'Set Alias';
    }
}

// ==========================================
// UI HELPERS
// ==========================================

function resetUIState() {
    browserSessionActive = false;

    document.getElementById('addPaymentBtn').disabled = false;
    document.getElementById('addPaymentBtn').querySelector('.btn-text').textContent = 'Add Payment';
    // Skip Account button stays enabled
    document.getElementById('cardAlias').disabled = true;
    document.getElementById('setAliasBtn').disabled = true;
    document.getElementById('setAliasBtn').querySelector('.btn-text').textContent = 'Set Alias';

    // Reset instruction steps
    document.querySelectorAll('.instruction-list li').forEach(li => {
        li.classList.remove('active', 'complete');
    });
}

function updateInstructionStep(stepNum, active = false) {
    // Mark previous steps as complete
    for (let i = 1; i < stepNum; i++) {
        const step = document.getElementById(`step${i}`);
        if (step) {
            step.classList.remove('active');
            step.classList.add('complete');
        }
    }

    // Mark current step
    const currentStep = document.getElementById(`step${stepNum}`);
    if (currentStep) {
        currentStep.classList.remove('complete');
        if (active) {
            currentStep.classList.add('active');
        }
    }
}

function markAllStepsComplete() {
    document.querySelectorAll('.instruction-list li').forEach(li => {
        li.classList.remove('active');
        li.classList.add('complete');
    });
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
