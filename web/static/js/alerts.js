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

// All alerts data (unfiltered)
let allAlerts = [];

// Pagination state
let currentPage = 1;
const itemsPerPage = 50;
let totalPages = 1;
let filteredAlerts = [];

// Current filters
let currentFilters = {
    symbols: [],
    timeframes: [],
    directions: [],
    patterns: [],
    date: ''
};

// Unique values for filter options
let uniqueValues = {
    symbols: new Set(),
    timeframes: new Set(),
    directions: new Set(),
    patterns: new Set()
};

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
    
    // Store all alerts
    allAlerts = [...alerts];
    
    // Clear loading message
    alertsTableBody.innerHTML = '';
    
    if (alerts.length === 0) {
        showNoAlerts();
        hidePagination();
    } else {
        // Update filter options with new data
        updateFilterOptions(alerts);
        
        // Apply current filters and setup pagination
        filteredAlerts = applyCurrentFilters(alerts);
        currentPage = 1;
        totalPages = Math.ceil(filteredAlerts.length / itemsPerPage);
        
        // Display first page
        displayCurrentPage();
        
        // Update counts
        totalAlerts = alerts.length;
        updateAlertCount(filteredAlerts.length);
        
        // Show/hide pagination
        if (filteredAlerts.length > itemsPerPage) {
            showPagination();
        } else {
            hidePagination();
        }
    }
});

// Receive new alert
socket.on('alert', (data) => {
    console.log('🚨 New alert received:', data);
    
    // Add to all alerts array at the beginning
    allAlerts.unshift(data);
    
    // Keep only last 1000 alerts in memory
    if (allAlerts.length > 1000) {
        allAlerts = allAlerts.slice(0, 1000);
    }
    
    // Update filter options
    updateFilterOptions([data]);
    
    // Check if alert passes current filters
    if (alertPassesFilters(data)) {
        // Add to filtered alerts at the beginning
        filteredAlerts.unshift(data);
        
        // Recalculate pagination
        totalPages = Math.ceil(filteredAlerts.length / itemsPerPage);
        
        // If we're on page 1, add the new alert to the display
        if (currentPage === 1) {
            // Remove "no alerts" message if exists
            if (alertsTableBody.querySelector('.no-alerts')) {
                alertsTableBody.innerHTML = '';
            }
            
            // Refresh current page to include new alert
            displayCurrentPage();
        }
        
        // Show browser notification
        showNotification(data);
        
        // Update pagination display
        if (filteredAlerts.length > itemsPerPage) {
            showPagination();
        }
    }
    
    // Update counter
    totalAlerts++;
    updateAlertCount(filteredAlerts.length);
    
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

/**
 * Format time that's already in GMT+7 from backend
 */
function formatTime(timeString) {
    try {
        // Backend now sends GMT+7 time
        const date = new Date(timeString);
        
        // Format as DD/MM HH:MM
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${day}/${month} ${hours}:${minutes}`;
    } catch (e) {
        console.error('Error formatting time:', e);
        return timeString;
    }
}

/**
 * Check if alert is from today (GMT+7)
 */
function isToday(timeString) {
    try {
        const date = new Date(timeString);
        const today = new Date();
        
        return date.getDate() === today.getDate() &&
               date.getMonth() === today.getMonth() &&
               date.getFullYear() === today.getFullYear();
    } catch (e) {
        return false;
    }
}

function addAlertToTable(alert, animate = true, insertAtTop = false) {
    const row = document.createElement('tr');
    if (animate) {
        row.className = 'new-alert-animation';
    }
    
    // Determine direction class for Long/Short badge
    const directionClass = alert.hướng === 'Long' ? 'direction-long' : 'direction-short';
    
    // Pattern group (G1, G2, G3) - plain text in "Nhóm" column
    const patternGroup = alert.nhóm || 'N/A';
    
    // Format price
    const price = alert.price ? `$${parseFloat(alert.price).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : 'N/A';
    
    // Format time (already GMT+7 from backend)
    const timeGMT7 = formatTime(alert.time_date);
    
    row.innerHTML = `
        <td><small>${timeGMT7}</small></td>
        <td><strong>${alert.mã}</strong></td>
        <td><span class="timeframe-badge">${alert.khung}</span></td>
        <td><span class="${directionClass}">${alert.hướng}</span></td>
        <td><small>${patternGroup}</small></td>
        <td><small>${price}</small></td>
        <td><a href="${alert.tradingview_link}" target="_blank" class="tradingview-link">
            <i class="fas fa-chart-line"></i>
        </a></td>
    `;
    
    // Just append - pagination handles ordering
    alertsTableBody.appendChild(row);
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

function updateAlertCount(filteredCount = null) {
    alertCount.textContent = totalAlerts;
    
    if (filteredCount !== null && filteredCount !== totalAlerts) {
        document.getElementById('filteredCount').style.display = 'inline';
        document.getElementById('filteredNumber').textContent = filteredCount;
    } else {
        document.getElementById('filteredCount').style.display = 'none';
    }
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
            window.open(alert.tradingview_link, '_blank');
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

/**
 * Filter Functions
 */

function toggleFilters() {
    const filterContent = document.getElementById('filterContent');
    filterContent.classList.toggle('show');
}

function updateFilterOptions(newAlerts) {
    // Add new values to unique sets
    newAlerts.forEach(alert => {
        uniqueValues.symbols.add(alert.mã || alert.symbol);
        uniqueValues.timeframes.add(alert.khung);
        uniqueValues.directions.add(alert.hướng);
        if (alert.nhóm) {
            uniqueValues.patterns.add(alert.nhóm);
        }
    });
    
    // Update symbol dropdown
    updateSelectOptions('symbolFilter', Array.from(uniqueValues.symbols).sort());
}

function updateSelectOptions(selectId, options) {
    const select = document.getElementById(selectId);
    const currentOptions = Array.from(select.options).map(option => option.value);
    
    options.forEach(value => {
        if (value && !currentOptions.includes(value)) {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        }
    });
}

function applyCurrentFilters(alerts) {
    return alerts.filter(alert => alertPassesFilters(alert));
}

function alertPassesFilters(alert) {
    // Check symbol filter
    if (currentFilters.symbols.length > 0) {
        const symbol = alert.mã || alert.symbol;
        if (!currentFilters.symbols.includes(symbol)) {
            return false;
        }
    }
    
    // Check timeframe filter
    if (currentFilters.timeframes.length > 0) {
        if (!currentFilters.timeframes.includes(alert.khung)) {
            return false;
        }
    }
    
    // Check direction filter
    if (currentFilters.directions.length > 0) {
        if (!currentFilters.directions.includes(alert.hướng)) {
            return false;
        }
    }
    
    // Check pattern group filter
    if (currentFilters.patterns.length > 0) {
        if (!alert.nhóm || !currentFilters.patterns.includes(alert.nhóm)) {
            return false;
        }
    }
    
    // Check date filter
    if (currentFilters.date === 'today') {
        if (!isToday(alert.time_date)) {
            return false;
        }
    }
    
    return true;
}

function applyFilters() {
    // Get selected values from each filter
    currentFilters.symbols = getSelectedValues('symbolFilter');
    currentFilters.timeframes = getSelectedValues('timeframeFilter');
    currentFilters.directions = getSelectedValues('directionFilter');
    currentFilters.patterns = getSelectedValues('patternFilter');
    currentFilters.date = document.getElementById('dateFilter').value;
    
    // Apply filters to all alerts
    filteredAlerts = applyCurrentFilters(allAlerts);
    
    // Reset to page 1 and recalculate pagination
    currentPage = 1;
    totalPages = Math.ceil(filteredAlerts.length / itemsPerPage);
    
    // Display first page
    displayCurrentPage();
    
    // Update alert count
    updateAlertCount(filteredAlerts.length);
    
    // Update active filters display
    updateActiveFiltersDisplay();
    
    // Show/hide pagination
    if (filteredAlerts.length > itemsPerPage) {
        showPagination();
    } else {
        hidePagination();
    }
    
    console.log(`🔍 Applied filters: ${filteredAlerts.length}/${allAlerts.length} alerts found, showing page ${currentPage} of ${totalPages}`);
}

function clearFilters() {
    // Reset all filters
    currentFilters = {
        symbols: [],
        timeframes: [],
        directions: [],
        patterns: [],
        date: ''
    };
    
    // Clear all select values
    ['symbolFilter', 'timeframeFilter', 'directionFilter', 'patternFilter', 'dateFilter'].forEach(id => {
        const select = document.getElementById(id);
        Array.from(select.options).forEach(option => option.selected = false);
    });
    
    // Reset filtered alerts and pagination
    filteredAlerts = [...allAlerts];
    currentPage = 1;
    totalPages = Math.ceil(filteredAlerts.length / itemsPerPage);
    
    // Display first page
    displayCurrentPage();
    
    // Update alert count
    updateAlertCount();
    
    // Clear active filters display
    updateActiveFiltersDisplay();
    
    // Show/hide pagination
    if (filteredAlerts.length > itemsPerPage) {
        showPagination();
    } else {
        hidePagination();
    }
    
    console.log('🗑️ Cleared all filters');
}

function getSelectedValues(selectId) {
    const select = document.getElementById(selectId);
    return Array.from(select.selectedOptions)
        .map(option => option.value)
        .filter(value => value !== '');
}

function updateActiveFiltersDisplay() {
    const activeFiltersContainer = document.getElementById('activeFilters');
    activeFiltersContainer.innerHTML = '';
    
    const filterTypes = [
        { key: 'symbols', label: 'Symbol', icon: 'fas fa-coins' },
        { key: 'timeframes', label: 'Timeframe', icon: 'fas fa-clock' },
        { key: 'directions', label: 'Direction', icon: 'fas fa-arrow-trend-up' },
        { key: 'patterns', label: 'Pattern', icon: 'fas fa-shapes' }
    ];
    
    // Add date filter if active
    if (currentFilters.date === 'today') {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        tag.innerHTML = `
            <i class="fas fa-calendar"></i>
            Ngày: Hôm nay
            <span class="remove" onclick="removeDateFilter()">×</span>
        `;
        activeFiltersContainer.appendChild(tag);
    }
    
    filterTypes.forEach(filterType => {
        const values = currentFilters[filterType.key];
        if (values.length > 0) {
            values.forEach(value => {
                const tag = document.createElement('div');
                tag.className = 'filter-tag';
                tag.innerHTML = `
                    <i class="${filterType.icon}"></i>
                    ${filterType.label}: ${value}
                    <span class="remove" onclick="removeFilter('${filterType.key}', '${value}')">×</span>
                `;
                activeFiltersContainer.appendChild(tag);
            });
        }
    });
}

function removeFilter(filterType, value) {
    // Remove value from filter
    currentFilters[filterType] = currentFilters[filterType].filter(v => v !== value);
    
    // Update select element
    const selectId = filterType.replace('s', '') + 'Filter'; // symbols -> symbolFilter
    const select = document.getElementById(selectId);
    Array.from(select.options).forEach(option => {
        if (option.value === value) {
            option.selected = false;
        }
    });
    
    // Reapply filters
    applyFilters();
}

function removeDateFilter() {
    currentFilters.date = '';
    document.getElementById('dateFilter').value = '';
    applyFilters();
}

/**
 * Pagination Functions
 */

function displayCurrentPage() {
    // Clear table
    alertsTableBody.innerHTML = '';
    
    // Calculate start and end indices
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredAlerts.length);
    
    // Get alerts for current page
    const pageAlerts = filteredAlerts.slice(startIndex, endIndex);
    
    if (pageAlerts.length === 0) {
        showNoAlerts();
    } else {
        pageAlerts.forEach(alert => addAlertToTable(alert, false));
    }
    
    // Update pagination UI
    updatePaginationUI();
}

function updatePaginationUI() {
    const startIndex = (currentPage - 1) * itemsPerPage + 1;
    const endIndex = Math.min(currentPage * itemsPerPage, filteredAlerts.length);
    
    // Update page info
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('rangeInfo').textContent = `Showing ${startIndex}-${endIndex} of ${filteredAlerts.length}`;
    
    // Update button states
    document.getElementById('firstPageBtn').disabled = currentPage === 1;
    document.getElementById('prevPageBtn').disabled = currentPage === 1;
    document.getElementById('nextPageBtn').disabled = currentPage === totalPages;
    document.getElementById('lastPageBtn').disabled = currentPage === totalPages;
}

function showPagination() {
    document.getElementById('paginationContainer').style.display = 'flex';
}

function hidePagination() {
    document.getElementById('paginationContainer').style.display = 'none';
}

function goToFirstPage() {
    if (currentPage !== 1) {
        currentPage = 1;
        displayCurrentPage();
    }
}

function goToPrevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayCurrentPage();
    }
}

function goToNextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        displayCurrentPage();
    }
}

function goToLastPage() {
    if (currentPage !== totalPages) {
        currentPage = totalPages;
        displayCurrentPage();
    }
}
