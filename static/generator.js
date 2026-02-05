// ==========================================
// Account Generator - Frontend Logic
// ==========================================

let isGmail = true;
let maxAccounts = 1;
let hasLocations = false;

document.addEventListener('DOMContentLoaded', function () {
    initializePage();
    setupEventListeners();
});

// Initialize page
async function initializePage() {
    await checkLocations();
    updateDropdown(1);
}

// Setup all event listeners
function setupEventListeners() {
    const form = document.getElementById('generatorForm');
    const clearBtn = document.getElementById('clearConsole');
    const emailInput = document.getElementById('email');
    const gmailBtn = document.getElementById('gmailType');
    const otherBtn = document.getElementById('otherType');

    // Register form submit handler
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    } else {
        console.error('Form not found!');
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', clearConsole);
    }

    // Email input - calculate max on change
    if (emailInput) {
        emailInput.addEventListener('input', debounce(calculateMaxAccounts, 500));
        emailInput.addEventListener('blur', calculateMaxAccounts);
    }

    // Email type toggle
    if (gmailBtn) {
        gmailBtn.addEventListener('click', () => setEmailType(true));
    }
    if (otherBtn) {
        otherBtn.addEventListener('click', () => setEmailType(false));
    }
}


// ==========================================
// EMAIL TYPE HANDLING
// ==========================================

function setEmailType(gmail) {
    isGmail = gmail;

    const gmailBtn = document.getElementById('gmailType');
    const otherBtn = document.getElementById('otherType');
    const emailHint = document.getElementById('emailHint');
    const emailInput = document.getElementById('email');

    if (gmail) {
        gmailBtn.classList.add('active');
        otherBtn.classList.remove('active');
        emailHint.textContent = 'Enter Gmail without dots for maximum variations';
        emailInput.placeholder = 'yourname@gmail.com';
    } else {
        gmailBtn.classList.remove('active');
        otherBtn.classList.add('active');
        emailHint.textContent = 'Non-Gmail: only 1 account will be created';
        emailInput.placeholder = 'your@email.com';

        // For non-Gmail, max is always 1
        updateDropdown(1);
        document.getElementById('countHint').textContent = 'Max: 1';
    }

    // Recalculate if email already entered
    if (emailInput.value) {
        calculateMaxAccounts();
    }
}

async function calculateMaxAccounts() {
    const email = document.getElementById('email').value.trim();
    const countHint = document.getElementById('countHint');

    if (!email || !email.includes('@')) {
        countHint.textContent = 'Enter email first';
        updateDropdown(1);
        return;
    }

    // Non-Gmail always 1
    if (!isGmail) {
        maxAccounts = 1;
        updateDropdown(1);
        countHint.textContent = 'Max: 1';
        return;
    }

    countHint.textContent = 'Calculating...';

    try {
        const response = await fetch('/api/generator/calculate-max', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const result = await response.json();

        maxAccounts = result.max || 1;
        updateDropdown(maxAccounts);

        if (result.duplicates_filtered > 0) {
            countHint.textContent = `Max: ${maxAccounts} (${result.duplicates_filtered} already used)`;
        } else {
            countHint.textContent = `Max: ${maxAccounts}`;
        }

        if (maxAccounts === 0) {
            countHint.textContent = 'All variations already used!';
            countHint.style.color = '#ef4444';
        } else {
            countHint.style.color = '';
        }

    } catch (error) {
        countHint.textContent = 'Error calculating';
        console.error('Calculate max error:', error);
    }
}

function updateDropdown(max) {
    const countSelect = document.getElementById('count');
    const currentValue = parseInt(countSelect.value) || 1;

    countSelect.innerHTML = '';

    const effectiveMax = Math.min(Math.max(max, 1), 100);

    for (let i = 1; i <= effectiveMax; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i;
        countSelect.appendChild(option);
    }

    // Restore previous selection if valid
    if (currentValue <= effectiveMax) {
        countSelect.value = currentValue;
    }
}

// ==========================================
// LOCATIONS
// ==========================================

async function checkLocations() {
    const statusText = document.getElementById('locationText');
    const statusIcon = document.querySelector('.status-icon');
    const badge = document.getElementById('locationBadge');

    try {
        const response = await fetch('/api/locations');
        const result = await response.json();

        hasLocations = result.has_locations;

        if (hasLocations) {
            statusText.textContent = `${result.count} location(s) available`;
            statusIcon.textContent = '✅';
            badge.textContent = 'Optional';
            badge.classList.remove('required');
        } else {
            statusText.textContent = 'No locations! You must add one below.';
            statusIcon.textContent = '⚠️';
            badge.textContent = 'Required';
            badge.classList.add('required');
        }

    } catch (error) {
        statusText.textContent = 'Error checking locations';
        statusIcon.textContent = '❌';
    }
}

// ==========================================
// VALIDATION FUNCTIONS
// ==========================================

function validatePassword(password) {
    const errors = [];

    if (password.length < 8) {
        errors.push('Password must be at least 8 characters');
    }
    if (!/[a-z]/.test(password)) {
        errors.push('Password must contain at least 1 lowercase letter');
    }
    if (!/[A-Z]/.test(password)) {
        errors.push('Password must contain at least 1 uppercase letter');
    }
    if (!/[0-9]/.test(password)) {
        errors.push('Password must contain at least 1 number');
    }

    return errors;
}

function validateGeolocation(geo) {
    if (!geo || geo.trim() === '') {
        return []; // Optional field, empty is OK
    }

    const errors = [];
    const pattern = /^-?\d+\.?\d*,\s*-?\d+\.?\d*$/;

    if (!pattern.test(geo.trim())) {
        errors.push('Geolocation must be in format: "29.452137, -98.642559"');
    }

    return errors;
}

function validateForm(data) {
    const allErrors = [];

    // Validate Email
    if (!data.email || !data.email.includes('@')) {
        allErrors.push('Valid email address is required');
    }

    // Validate Password
    const passwordErrors = validatePassword(data.password);
    allErrors.push(...passwordErrors);

    // Validate Geolocation (only if provided)
    if (data.geolocation && data.geolocation.trim() !== '') {
        const geoErrors = validateGeolocation(data.geolocation);
        allErrors.push(...geoErrors);
    }

    // Check location requirement
    if (!hasLocations && !data.geolocation && !data.fullAddress) {
        allErrors.push('No locations available. Please add geolocation and address below.');
    }

    return allErrors;
}

// ==========================================
// FORM HANDLING
// ==========================================

async function handleFormSubmit(event) {
    event.preventDefault();

    logToConsole('Submit triggered...', 'system');

    // Collect form data
    const formData = {
        email: document.getElementById('email').value.trim(),
        password: document.getElementById('password').value,
        count: parseInt(document.getElementById('count').value) || 1,
        isGmail: isGmail,
        geolocation: document.getElementById('geolocation').value.trim(),
        fullAddress: document.getElementById('fullAddress').value.trim()
    };

    logToConsole(`Preparing to submit, count: ${formData.count}`, 'system');

    // Validate
    const errors = validateForm(formData);

    if (errors.length > 0) {
        showErrorModal(errors);
        return;
    }

    // Check geo + address consistency
    const hasGeo = formData.geolocation !== '';
    const hasAddress = formData.fullAddress !== '';

    if ((hasGeo && !hasAddress) || (!hasGeo && hasAddress)) {
        showErrorModal(['If adding a new location, both Geolocation AND Full Address are required']);
        return;
    }

    // Start generation
    startGeneration(formData);
}

async function startGeneration(formData) {
    const btn = document.getElementById('generateBtn');
    const btnText = btn.querySelector('.btn-text');

    // Update UI
    btn.disabled = true;
    btnText.textContent = 'Generating...';

    logToConsole('Starting process...', 'info');
    logToConsole(`Email: ${formData.email}`, 'system');
    logToConsole(`Email Type: ${formData.isGmail ? 'Gmail (dot variations)' : 'Other'}`, 'system');
    logToConsole(`Accounts to register: ${formData.count}`, 'system');

    if (formData.geolocation && formData.fullAddress) {
        logToConsole(`Custom location: ${formData.fullAddress}`, 'system');
    }

    try {
        // Send to backend
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (result.status === 'started') {
            logToConsole('Generation started. Monitoring progress...', 'info');
            pollStatus();
        } else if (result.status === 'error') {
            if (result.errors) {
                result.errors.forEach(err => logToConsole(`Error: ${err}`, 'error'));
            } else {
                logToConsole(`Error: ${result.message}`, 'error');
            }
            resetButton();
        }

    } catch (error) {
        logToConsole(`Network error: ${error.message}`, 'error');
        resetButton();
    }
}

async function pollStatus() {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/generate/status');
            const status = await response.json();

            // Log any new messages
            if (status.messages && status.messages.length > 0) {
                status.messages.forEach(msg => {
                    logToConsole(msg.text, msg.type || 'info');
                });
            }

            // Check if complete
            if (status.status === 'complete') {
                logToConsole('✅ Generation complete!', 'success');
                clearInterval(pollInterval);
                resetButton();

                // Recalculate max (some emails now used)
                calculateMaxAccounts();
            } else if (status.status === 'error') {
                logToConsole(`❌ Error: ${status.message}`, 'error');
                clearInterval(pollInterval);
                resetButton();
            }

        } catch (error) {
            logToConsole(`Status check failed: ${error.message}`, 'warning');
        }
    }, 1000);
}

function resetButton() {
    const btn = document.getElementById('generateBtn');
    const btnText = btn.querySelector('.btn-text');
    btn.disabled = false;
    btnText.textContent = 'Start Process';
}

// ==========================================
// CONSOLE OUTPUT
// ==========================================

function logToConsole(message, type = 'info') {
    const console = document.getElementById('consoleOutput');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;

    const timestamp = new Date().toLocaleTimeString();
    line.textContent = `[${timestamp}] ${message}`;

    console.appendChild(line);
    console.scrollTop = console.scrollHeight;
}

function clearConsole() {
    const console = document.getElementById('consoleOutput');
    console.innerHTML = '<div class="console-line system">Console cleared. Ready for new generation.</div>';
}

// ==========================================
// ERROR MODAL
// ==========================================

function showErrorModal(errors) {
    const modal = document.getElementById('errorModal');
    const errorList = document.getElementById('errorList');

    // Populate error list
    errorList.innerHTML = '';
    errors.forEach(error => {
        const li = document.createElement('li');
        li.textContent = error;
        errorList.appendChild(li);
    });

    // Show modal
    modal.classList.remove('hidden');
}

function closeModal() {
    const modal = document.getElementById('errorModal');
    modal.classList.add('hidden');
}

// Close modal on outside click
document.addEventListener('click', function (event) {
    const modal = document.getElementById('errorModal');
    if (event.target === modal) {
        closeModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
        closeModal();
    }
});

// ==========================================
// UTILITIES
// ==========================================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
