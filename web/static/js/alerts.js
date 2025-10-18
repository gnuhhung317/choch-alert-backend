/**
 * CHoCH Alert Dashboard - Real-time alerts via SocketIO
 */

// Initialize SocketIO connection
const socket = io();

// DOM elements
const connectionStatus = document.getElementById('connectionStatus');
const alertsTableBody = document.getElementById('alertsTableBody');
const alertCount = document.getElementById('alertCount');

// Alert counter
let totalAlerts = 0;

// Request notification permission on page load
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

/**
 * Socket.IO event handlers
 */

// Connection established
socket.on('connect', () => {
    console.log('✅ Connected to server');
    updateConnectionStatus(true);
    
    // Request alert history
    socket.emit('request_history');
});

// Connection lost
socket.on('disconnect', () => {
    console.log('❌ Disconnected from server');
    updateConnectionStatus(false);
});

// Receive alert history
socket.on('alerts_history', (alerts) => {
    console.log(`📊 Received ${alerts.length} alerts from history`);
    
    // Clear loading message
    alertsTableBody.innerHTML = '';
    
    if (alerts.length === 0) {
        showNoAlerts();
    } else {
        alerts.forEach(alert => addAlertToTable(alert, false));
        totalAlerts = alerts.length;
        updateAlertCount();
    }
});

// Receive new alert
socket.on('alert', (data) => {
    console.log('🚨 New alert received:', data);
    
    // Remove "no alerts" message if exists
    if (alertsTableBody.querySelector('.no-alerts')) {
        alertsTableBody.innerHTML = '';
    }
    
    // Add to table with animation
    addAlertToTable(data, true);
    
    // Update counter
    totalAlerts++;
    updateAlertCount();
    
    // Show browser notification
    showNotification(data);
    
    // Play sound (optional)
    // playAlertSound();
});

/**
 * Helper functions
 */

function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.className = 'status-badge status-connected';
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Connected';
    } else {
        connectionStatus.className = 'status-badge status-disconnected';
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

function addAlertToTable(alert, animate = true) {
    const row = document.createElement('tr');
    if (animate) {
        row.className = 'new-alert-animation';
    }
    
    // Determine direction class
    const directionClass = alert.hướng === 'Long' ? 'direction-long' : 'direction-short';
    
    // Format price
    const price = alert.price ? `$${parseFloat(alert.price).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : 'N/A';
    
    row.innerHTML = `
        <td>${alert.time_date}</td>
        <td><strong>${alert.mã}</strong></td>
        <td><span class="timeframe-badge">${alert.khung}</span></td>
        <td><span class="${directionClass}">${alert.hướng}</span></td>
        <td>${alert.loại}</td>
        <td>${price}</td>
        <td><a href="${alert.link}" target="_blank" class="tradingview-link">
            <i class="fas fa-external-link-alt"></i> View Chart
        </a></td>
    `;
    
    // Insert at the beginning
    alertsTableBody.insertBefore(row, alertsTableBody.firstChild);
    
    // Keep only last 100 rows
    while (alertsTableBody.children.length > 100) {
        alertsTableBody.removeChild(alertsTableBody.lastChild);
    }
}

function showNoAlerts() {
    alertsTableBody.innerHTML = `
        <tr>
            <td colspan="7" class="no-alerts">
                <i class="fas fa-inbox fa-3x mb-3" style="color: #ccc;"></i>
                <p>No alerts yet. Waiting for CHoCH signals...</p>
            </td>
        </tr>
    `;
}

function updateAlertCount() {
    alertCount.textContent = totalAlerts;
}

function showNotification(alert) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const title = `CHoCH ${alert.hướng} on ${alert.khung}`;
        const options = {
            body: `${alert.mã} - ${alert.loại}\nPrice: $${alert.price}`,
            icon: '/static/favicon.ico',
            badge: '/static/favicon.ico',
            tag: `choch-${Date.now()}`,
            requireInteraction: false
        };
        
        const notification = new Notification(title, options);
        
        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
        
        // Open TradingView on click
        notification.onclick = () => {
            window.open(alert.link, '_blank');
            notification.close();
        };
    }
}

function playAlertSound() {
    // Optional: play sound on new alert
    // const audio = new Audio('/static/alert.mp3');
    // audio.play().catch(e => console.log('Could not play sound:', e));
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 CHoCH Alert Dashboard initialized');
    
    // Check notification permission
    if ('Notification' in window) {
        console.log(`📢 Notification permission: ${Notification.permission}`);
    }
});
