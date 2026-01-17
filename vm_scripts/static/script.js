// This is our script.js for our project
// Room icons - added emojis to make our page nicer
const roomIcons = {
    'living_room': '🛋️',
    'kitchen': '🍳',
    'bedroom': '🛏️'
};

// Fetching with timeout - prevents the page from hanging if the server is slow
function fetchWithTimeout(url, timeout = 5000) {
    return Promise.race([
        fetch(url),
        new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Request timeout')), timeout)
        )
    ]);
}

// Loading current room status cards - this shows the latest reading from each room
function loadRoomCards() {
    fetchWithTimeout('/api/latest', 3000)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('room-cards');
            
            // If there is no data available, there will be a message
            if (data.length === 0) {
                container.innerHTML = '<div class="loading"><p>No room data available</p></div>';
                return;
            }

            // Building the HTML for each room card
            let html = '';
            for (let i = 0; i < data.length; i++) {
                const room = data[i];
                html += `
                    <div class="room-card">
                        <div class="room-header">
                            <div class="room-icon">${roomIcons[room.room] || '🏠'}</div>
                            <div class="room-title">
                                <h2>${room.room.replace('_', ' ')}</h2>
                                <div class="device-id">${room.device_id}</div>
                            </div>
                        </div>
                        
                        <div class="sensor-grid">
                            <div class="sensor-box">
                                <div class="sensor-label"><i class="fas fa-thermometer-half"></i> Temperature</div>
                                <div class="sensor-value ${room.temp_status !== 'NORMAL' ? 'value-alert' : ''}">${room.temperature}°C</div>
                                <span class="sensor-status status-${room.temp_status.toLowerCase()}">${room.temp_status}</span>
                            </div>
                            
                            <div class="sensor-box">
                                <div class="sensor-label"><i class="fas fa-tint"></i> Humidity</div>
                                <div class="sensor-value">${room.humidity}%</div>
                                <span class="sensor-status status-normal">${room.humidity_status || 'NORMAL'}</span>
                            </div>
                            
                            <div class="sensor-box">
                                <div class="sensor-label"><i class="fas fa-wind"></i> Air Quality</div>
                                <div class="sensor-value ${room.air_status === 'POOR' ? 'value-alert' : ''}">${room.air_quality}</div>
                                <span class="sensor-status status-${room.air_status.toLowerCase()}">${room.air_status}</span>
                            </div>
                            
                            <div class="sensor-box">
                                <div class="sensor-label"><i class="fas fa-lightbulb"></i> Light Level</div>
                                <div class="sensor-value">${room.light_level}</div>
                                <span class="sensor-status status-normal">lux</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        })
        .catch(err => {
            console.error('Error loading room cards:', err);
            document.getElementById('room-cards').innerHTML = 
                '<div class="loading"><p style="color: red;">Failed to load room data</p></div>';
        });
}

// Loads statistics - shows average values and counts per room
function loadStats() {
    fetchWithTimeout('/api/stats', 3000)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('stats-grid');
            
            if (data.length === 0) {
                container.innerHTML = '<div class="loading"><p>No statistics available</p></div>';
                return;
            }

            let html = '';
            for (let i = 0; i < data.length; i++) {
                const stat = data[i];
                html += `
                    <div class="stat-card">
                        <h3>${roomIcons[stat.room] || '🏠'} ${stat.room.replace('_', ' ')}</h3>
                        <div class="stat-value">${stat.total_readings}</div>
                        <div class="stat-label">Total Readings</div>
                        <hr style="margin: 15px 0; border: none; border-top: 1px solid rgba(255,255,255,0.3);">
                        <div style="font-size: 14px;">
                            <div style="margin: 5px 0;">Avg Temp: ${stat.avg_temp.toFixed(1)}°C</div>
                            <div style="margin: 5px 0;">Avg Humidity: ${stat.avg_humidity.toFixed(1)}%</div>
                            <div style="margin: 5px 0;">Temp Alerts: ${stat.temp_alerts}</div>
                            <div style="margin: 5px 0;">Air Alerts: ${stat.air_alerts}</div>
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        })
        .catch(err => {
            console.error('Error loading stats:', err);
            document.getElementById('stats-grid').innerHTML = 
                '<div class="loading"><p style="color: red;">Failed to load statistics</p></div>';
        });
}

// Loads history table - shows the last 50 readings
function loadHistory() {
    fetchWithTimeout('/api/readings', 5000)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('history-body');
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="loading">No history available</td></tr>';
                return;
            }

            let html = '';
            for (let i = 0; i < data.length; i++) {
                const row = data[i];
                html += `
                    <tr>
                        <td>${new Date(row.timestamp).toLocaleString()}</td>
                        <td><span class="room-badge room-${row.room}">${roomIcons[row.room] || '🏠'} ${row.room.replace('_', ' ')}</span></td>
                        <td>${row.device_id}</td>
                        <td class="${row.temp_status !== 'NORMAL' ? 'value-alert' : ''}">${row.temperature}</td>
                        <td><span class="sensor-status status-${row.temp_status.toLowerCase()}">${row.temp_status}</span></td>
                        <td>${row.humidity}</td>
                        <td class="${row.air_status === 'POOR' ? 'value-alert' : ''}">${row.air_quality}</td>
                        <td><span class="sensor-status status-${row.air_status.toLowerCase()}">${row.air_status}</span></td>
                        <td>${row.light_level}</td>
                    </tr>
                `;
            }
            tbody.innerHTML = html;
        })
        .catch(err => {
            console.error('Error loading history:', err);
            document.getElementById('history-body').innerHTML = 
                '<tr><td colspan="9" class="loading" style="color: red;">Failed to load history</td></tr>';
        });
}

// Updates everything - room cards, stats, history, and timestamp
function updateAllData() {
    loadRoomCards();
    loadStats();
    loadHistory();
    
    document.getElementById('last-update').innerHTML = 
        '<i class="fas fa-clock"></i> Last update: ' + new Date().toLocaleTimeString();
}

// Loads everything when page first loads
updateAllData();

// Auto-refresh everything every 15 seconds
setInterval(updateAllData, 15000);