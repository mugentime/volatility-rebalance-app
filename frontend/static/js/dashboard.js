// Binance Volatility Strategy Dashboard JavaScript

// Global variables
let authToken = null;
let portfolioData = null;
let ltvChart = null;
let updateInterval = null;

// API base URL
const API_BASE = '/api';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    checkExistingAuth();
});

function initializeEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);

    // Register form
    document.getElementById('registerForm').addEventListener('submit', handleRegister);

    // Initialize LTV gauge
    initializeLTVGauge();
}

function checkExistingAuth() {
    const token = localStorage.getItem('authToken');
    if (token) {
        authToken = token;
        showDashboard();
        startDataUpdates();
    }
}

// Authentication functions
async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('username', data.username);

            showDashboard();
            startDataUpdates();
        } else {
            showError(data.error || 'Login failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Login error:', error);
    }
}

async function handleRegister(event) {
    event.preventDefault();

    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Account created successfully! Please login.');
            showLogin();
        } else {
            showError(data.error || 'Registration failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Registration error:', error);
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');

    if (updateInterval) {
        clearInterval(updateInterval);
    }

    showLogin();
}

// UI functions
function showLogin() {
    document.getElementById('loginModal').style.display = 'block';
    document.getElementById('registerModal').style.display = 'none';
    document.getElementById('dashboard').style.display = 'none';
}

function showRegister() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('registerModal').style.display = 'block';
    document.getElementById('dashboard').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('registerModal').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';

    const username = localStorage.getItem('username');
    document.getElementById('welcomeUser').textContent = `Welcome, ${username}`;
}

function showError(message) {
    alert(`Error: ${message}`);
}

function showSuccess(message) {
    alert(`Success: ${message}`);
}

// Data update functions
function startDataUpdates() {
    updatePortfolioData();
    updateTransactions();
    updateAlerts();

    // Update every 30 seconds
    updateInterval = setInterval(() => {
        updatePortfolioData();
        updateTransactions();
        updateAlerts();
    }, 30000);
}

async function updatePortfolioData() {
    try {
        const response = await fetch(`${API_BASE}/portfolio/status`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            portfolioData = await response.json();
            updatePortfolioDisplay();
            updateLTVGauge();
        } else if (response.status === 404) {
            // Portfolio not initialized
            updatePortfolioDisplay(null);
        }
    } catch (error) {
        console.error('Error updating portfolio data:', error);
    }
}

function updatePortfolioDisplay(data = portfolioData) {
    if (!data) {
        document.getElementById('portfolioStatus').textContent = 'Not Initialized';
        document.getElementById('ltvRatio').textContent = '0.00%';
        document.getElementById('lastUpdate').textContent = 'Never';
        document.getElementById('totalValue').textContent = '$0.00';
        document.getElementById('ethBalance').textContent = '0.0000 ETH';
        document.getElementById('solBalance').textContent = '0.0000 SOL';
        document.getElementById('profitLoss').textContent = '$0.00';
        return;
    }

    // Status bar
    document.getElementById('portfolioStatus').textContent = data.status.toUpperCase();
    document.getElementById('ltvRatio').textContent = `${(data.current_ltv * 100).toFixed(2)}%`;
    document.getElementById('lastUpdate').textContent = formatTime(data.last_updated);

    // Portfolio overview
    document.getElementById('totalValue').textContent = `$${data.total_value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('ethBalance').textContent = `${data.eth_balance.toFixed(4)} ETH`;
    document.getElementById('solBalance').textContent = `${data.sol_balance.toFixed(4)} SOL`;

    const pnl = data.total_profit_loss || 0;
    const pnlElement = document.getElementById('profitLoss');
    pnlElement.textContent = `$${pnl.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    pnlElement.style.color = pnl >= 0 ? '#28a745' : '#dc3545';

    // Update button states
    updateButtonStates(data.status);
}

function updateButtonStates(status) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const rebalanceBtn = document.getElementById('rebalanceBtn');
    const emergencyBtn = document.getElementById('emergencyBtn');

    if (status === 'active') {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        rebalanceBtn.disabled = false;
        emergencyBtn.disabled = false;
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        rebalanceBtn.disabled = true;
        emergencyBtn.disabled = true;
    }
}

// LTV Gauge
function initializeLTVGauge() {
    const ctx = document.getElementById('ltvGauge').getContext('2d');

    ltvChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#28a745', '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: Math.PI,
            rotation: Math.PI,
            cutout: '80%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        }
    });
}

function updateLTVGauge() {
    if (!ltvChart || !portfolioData) return;

    const ltv = portfolioData.current_ltv * 100;
    const remaining = 100 - ltv;

    // Color based on risk level
    let color = '#28a745'; // Safe - green
    if (ltv > 65) color = '#dc3545'; // Danger - red
    else if (ltv > 55) color = '#ffc107'; // Target - yellow

    ltvChart.data.datasets[0].data = [ltv, remaining];
    ltvChart.data.datasets[0].backgroundColor = [color, '#e9ecef'];
    ltvChart.update('none');

    // Update center text (custom implementation would be needed)
    // For now, we'll update the status display
}

// Strategy control functions
async function initializePortfolio() {
    const initialCapital = document.getElementById('initialCapital').value;

    if (!initialCapital || initialCapital < 100) {
        showError('Please enter a valid initial capital (minimum $100)');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/portfolio/initialize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ initial_capital_usd: parseFloat(initialCapital) })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Portfolio initialized successfully!');
            updatePortfolioData();
        } else {
            showError(data.error || 'Failed to initialize portfolio');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Initialize portfolio error:', error);
    }
}

async function startStrategy() {
    try {
        const response = await fetch(`${API_BASE}/portfolio/start`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Strategy started successfully!');
            updatePortfolioData();
        } else {
            showError(data.error || 'Failed to start strategy');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Start strategy error:', error);
    }
}

async function stopStrategy() {
    try {
        const response = await fetch(`${API_BASE}/portfolio/stop`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Strategy stopped successfully!');
            updatePortfolioData();
        } else {
            showError(data.error || 'Failed to stop strategy');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Stop strategy error:', error);
    }
}

async function manualRebalance() {
    try {
        const response = await fetch(`${API_BASE}/manual/rebalance`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Manual rebalance completed!');
            updatePortfolioData();
        } else {
            showError(data.error || 'Failed to execute rebalance');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Manual rebalance error:', error);
    }
}

async function emergencyStop() {
    if (!confirm('Are you sure you want to execute an emergency stop? This will liquidate all positions.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/portfolio/emergency-stop`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Emergency stop executed!');
            updatePortfolioData();
        } else {
            showError(data.error || 'Failed to execute emergency stop');
        }
    } catch (error) {
        showError('Network error. Please try again.');
        console.error('Emergency stop error:', error);
    }
}

// Transaction display
async function updateTransactions() {
    try {
        const response = await fetch(`${API_BASE}/transactions?per_page=10`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            displayTransactions(data.transactions);
        }
    } catch (error) {
        console.error('Error updating transactions:', error);
    }
}

function displayTransactions(transactions) {
    const container = document.getElementById('transactionsList');

    if (!transactions || transactions.length === 0) {
        container.innerHTML = '<div class="loading">No transactions found</div>';
        return;
    }

    container.innerHTML = transactions.map(tx => `
        <div class="transaction-item">
            <div>
                <div class="transaction-type">${tx.type}</div>
                <div class="transaction-time">${formatTime(tx.timestamp)}</div>
            </div>
            <div class="transaction-amount">
                ${tx.eth_amount > 0 ? `${tx.eth_amount.toFixed(4)} ETH` : ''}
                ${tx.sol_amount > 0 ? `${tx.sol_amount.toFixed(4)} SOL` : ''}
                ${tx.usd_value > 0 ? `$${tx.usd_value.toFixed(2)}` : ''}
            </div>
        </div>
    `).join('');
}

// Alerts display
async function updateAlerts() {
    try {
        const response = await fetch(`${API_BASE}/alerts`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            displayAlerts(data.alerts);
        }
    } catch (error) {
        console.error('Error updating alerts:', error);
    }
}

function displayAlerts(alerts) {
    const container = document.getElementById('alertsList');

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="loading">No alerts</div>';
        return;
    }

    container.innerHTML = alerts.slice(0, 5).map(alert => `
        <div class="alert-item ${alert.severity.toLowerCase()}">
            <div class="alert-title">${alert.title}</div>
            <div class="alert-message">${alert.message}</div>
            <div class="alert-time">${formatTime(alert.created_at)}</div>
        </div>
    `).join('');
}

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return 'Never';

    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Error handling for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});
