// Global state
let teamToken = null;

// UI Functions
function showNotification(message, type = 'info') {
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 5000);
}

// Modal Functions
async function getCameraList() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.filter(device => device.kind === 'videoinput');
}

async function tryStartCamera(cameraId) {
    try {
        await html5QrCode.start(
            cameraId,
            {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            },
            (decodedText) => {
                closeQRScanner();
                // Extract token if it's a full URL, otherwise use as is
                const token = decodedText.includes('?t=') ? 
                    new URLSearchParams(decodedText.split('?')[1]).get('t') : 
                    decodedText;
                window.location.href = `/scan?t=${encodeURIComponent(token)}`;
            },
            (error) => {
                // Handle scan errors silently
            }
        );
        currentCameraId = cameraId;
        return true;
    } catch (err) {
        console.log(`Failed to start camera ${cameraId}:`, err);
        return false;
    }
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Navigation toggle
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        // Close mobile menu when clicking on a link
        navMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
    }
});

// Scan modal functions
function openScanOptions() {
    document.getElementById('scan-modal').style.display = 'block';
}

function closeScanModal() {
    document.getElementById('scan-modal').style.display = 'none';
}

function openManualEntry() {
    closeScanModal();
    document.getElementById('manual-entry-modal').style.display = 'block';
}

function closeManualEntry() {
    document.getElementById('manual-entry-modal').style.display = 'none';
    document.getElementById('manual-token').value = '';
}

function manualScan() {
    const token = document.getElementById('manual-token').value.trim();
    if (!token) {
        showNotification('Please enter a token', 'error');
        return;
    }
    window.location.href = `/scan?t=${encodeURIComponent(token)}`;
}

// QR Scanner functions
async function checkCameraPermission() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach(track => track.stop());
        return true;
    } catch (err) {
        return false;
    }
}

async function requestCameraPermission() {
    try {
        // First check if getUserMedia is supported
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera API is not supported in this browser');
        }

        // Check if we're on HTTPS or localhost
        const isLocalhost = window.location.hostname === 'localhost' || 
                          window.location.hostname === '127.0.0.1';
        const isSecure = window.location.protocol === 'https:';

        if (!isLocalhost && !isSecure) {
            throw new Error('Camera access requires HTTPS or localhost');
        }

        const result = await checkCameraPermission();
        if (!result) {
            showNotification("Please allow camera access when prompted", "info");
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
        }
        return true;
    } catch (err) {
        let errorMessage = '';
        
        if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            errorMessage = 'No camera found. Please ensure your device has a camera.';
        } else if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            const isChrome = /Chrome/.test(navigator.userAgent);
            const isFirefox = /Firefox/.test(navigator.userAgent);
            
            if (isChrome) {
                errorMessage = 'Camera access denied. To enable:\n' +
                    '1. Click the camera icon in the address bar or\n' +
                    '2. Open Chrome Settings → Privacy and security → Site Settings → Camera';
            } else if (isFirefox) {
                errorMessage = 'Camera access denied. To enable:\n' +
                    '1. Click the camera icon in the address bar or\n' +
                    '2. Open Firefox Settings → Privacy & Security → Permissions → Camera';
            } else {
                errorMessage = 'Camera permission denied. Please enable it in your browser settings.';
            }
        } else if (err.message.includes('HTTPS')) {
            errorMessage = 'Camera access requires HTTPS. Please use HTTPS or localhost.';
        } else {
            errorMessage = `Camera error: ${err.message}`;
        }
        
        showNotification(errorMessage, "error");
        return false;
    }
}

async function startQRScanner() {
    closeScanModal();
    document.getElementById('qr-scanner-modal').style.display = 'block';
    document.getElementById('qr-reader').innerHTML = ''; // Clear previous content
    
    try {
        const hasPermission = await requestCameraPermission();
        if (!hasPermission) {
            document.getElementById('qr-reader').innerHTML = `
                <div class="camera-permission-error">
                    <p>⚠️ Camera access is required to scan QR codes.</p>
                    <button onclick="requestCameraPermission().then(result => { if(result) startQRScanner(); })" class="btn-primary">
                        Grant Camera Access
                    </button>
                </div>
            `;
            return;
        }

        // Get list of available video devices
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');

        if (videoDevices.length === 0) {
            throw new Error('No camera devices found');
        }

        // Clean up existing instance if any
        if (html5QrCode && html5QrCode.isScanning) {
            await html5QrCode.stop();
        }
        html5QrCode = new Html5Qrcode("qr-reader");

        // Show loading state
        document.getElementById('qr-reader').innerHTML = `
            <div class="camera-loading">
                <p>📸 Initializing camera...</p>
            </div>
        `;

        // Try to start with the first available camera
        let cameraStarted = false;
        for (const device of videoDevices) {
            try {
                await html5QrCode.start(
                    device.deviceId,
                    {
                        fps: 10,
                        qrbox: { width: 250, height: 250 },
                        aspectRatio: 1.0
                    },
            (decodedText) => {
                // On successful scan
                closeQRScanner();
                window.location.href = `/scan?t=${encodeURIComponent(decodedText)}`;
            },
            (error) => {
                // Handle scan errors silently
            }
        );
    } catch (err) {
        console.error("QR Scanner initialization failed:", err);
        const errorMessage = err.message;
        const isPermissionError = errorMessage.includes('permission') || 
                                errorMessage.includes('Permission') ||
                                errorMessage.includes('denied');
                                
        document.getElementById('qr-reader').innerHTML = `
            <div class="camera-permission-error">
                <p>⚠️ Failed to start camera.</p>
                <p class="error-details">${errorMessage}</p>
                ${isPermissionError ? `
                    <div class="permission-instructions">
                        <p><strong>To fix this:</strong></p>
                        <ol>
                            <li>Look for the camera icon in your browser's address bar</li>
                            <li>Click it and select "Allow"</li>
                            <li>If not found, follow your browser's instructions below</li>
                        </ol>
                        <p><strong>Chrome:</strong> Settings → Privacy and security → Site Settings → Camera</p>
                        <p><strong>Firefox:</strong> Settings → Privacy & Security → Permissions → Camera</p>
                        <p><strong>Safari:</strong> Preferences → Websites → Camera</p>
                    </div>
                ` : ''}
                <button onclick="startQRScanner()" class="btn-primary">
                    Try Again
                </button>
            </div>
        `;
    }
}

function closeQRScanner() {
    const modal = document.getElementById('qr-scanner-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    if (html5QrCode && html5QrCode.isScanning) {
        html5QrCode.stop().catch(err => console.error("Failed to stop QR scanner:", err));
    }
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('manual-scan-modal');
    if (event.target === modal) {
        closeManualScan();
    }
});

// Handle Enter key in manual scan input
document.addEventListener('DOMContentLoaded', function() {
    const manualTokenInput = document.getElementById('manual-token');
    if (manualTokenInput) {
        manualTokenInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                manualScan();
            }
        });
    }
});

// Team action function (for scan page)
function teamAction(token, action) {
    const byWho = prompt("Who is performing this action?") || "Unknown";
    
    fetch('/api/team/action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            token: token,
            action: action,
            by_who: byWho
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Team marked ${action.toUpperCase()} successfully!`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update team status', 'error');
    });
}

// Member action function (for scan page)
function memberAction(memberId, action) {
    const byWho = prompt("Who is performing this action?") || "Unknown";
    
    fetch('/api/member/action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            member_id: memberId,
            action: action,
            by_who: byWho
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Member marked ${action.toUpperCase()} successfully!`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update member status', 'error');
    });
}

// Dashboard functions
let allTeams = [];
let currentFilter = 'all';

function fetchStats() {
    const button = document.querySelector('.dashboard-header button');
    if (button) {
        button.disabled = true;
        button.textContent = 'Loading...';
    }
    
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update stats
            updateElement('team-present', data.teams.present);
            updateElement('team-total', data.teams.total);
            updateElement('member-present', data.members.present);
            updateElement('member-total', data.members.total);
            
            // Calculate rates
            const teamRate = data.teams.total > 0 ? Math.round((data.teams.present / data.teams.total) * 100) : 0;
            const memberRate = data.members.total > 0 ? Math.round((data.members.present / data.members.total) * 100) : 0;
            
            updateElement('team-rate', teamRate + '%');
            updateElement('member-rate', memberRate + '%');
            
            // Store and display teams
            allTeams = data.team_list;
            displayTeams(allTeams);
            
            showNotification('Stats updated successfully!', 'success');
        })
        .catch(error => {
            console.error('Error:', error);
            const container = document.getElementById('teams-list');
            if (container) {
                container.innerHTML = '<div class="error">Failed to load data</div>';
            }
            showNotification('Failed to load data', 'error');
        })
        .finally(() => {
            if (button) {
                button.disabled = false;
                button.textContent = '🔄 Fetch Latest';
            }
        });
}

function displayTeams(teams) {
    const container = document.getElementById('teams-list');
    if (!container) return;
    
    if (teams.length === 0) {
        container.innerHTML = '<div class="no-teams">No teams found</div>';
        return;
    }
    
    const html = teams.map(team => `
        <div class="team-row ${team.is_present ? 'team-present' : 'team-absent'}">
            <div class="team-main-info">
                <h3>${escapeHtml(team.name)}</h3>
                <p class="team-id">ID: ${escapeHtml(team.team_id)}</p>
                <p class="team-college">${escapeHtml(team.college)}</p>
            </div>
            <div class="team-stats">
                <div class="member-count">
                    <span class="present">${team.members_present || 0}</span> / 
                    <span class="total">${team.member_count}</span> members present
                </div>
                <span class="team-status ${team.is_present ? 'status-present' : 'status-absent'}">
                    ${team.is_present ? '✅ Team Present' : '❌ Team Absent'}
                </span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function filterTeams(filter) {
    currentFilter = filter;
    
    // Update button states
    document.querySelectorAll('.filter-controls .btn').forEach(btn => btn.classList.remove('active'));
    const activeButton = document.getElementById(`filter-${filter}`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Filter teams
    let filteredTeams = allTeams;
    if (filter === 'present') {
        filteredTeams = allTeams.filter(team => team.is_present);
    } else if (filter === 'absent') {
        filteredTeams = allTeams.filter(team => !team.is_present);
    }
    
    displayTeams(filteredTeams);
}

// Utility functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${escapeHtml(message)}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#48bb78' : type === 'error' ? '#f56565' : '#4c51bf'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 1rem;
        max-width: 400px;
        animation: slideIn 0.3s ease;
    `;
    
    // Add animation keyframes if not exists
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            .notification button {
                background: none;
                border: none;
                color: white;
                font-size: 1.2rem;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background 0.2s;
            }
            .notification button:hover {
                background: rgba(255,255,255,0.2);
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Initialize QR Scanner
function initQRScanner() {
    const qrContainer = document.getElementById('qr-reader');
    if (!qrContainer) return;

    const html5QrCode = new Html5Qrcode("qr-reader");
    const qrConfig = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
    };

    html5QrCode.start(
        { facingMode: "environment" },
        qrConfig,
        (decodedText) => {
            // On successful scan
            html5QrCode.stop();
            window.location.href = `/scan?t=${encodeURIComponent(decodedText)}`;
        },
        (error) => {
            // Handle scan errors silently
        }
    ).catch((err) => {
        console.error("QR Scanner initialization failed:", err);
        showNotification("Failed to start camera. Please check camera permissions.", "error");
    });
}

// Initialize dashboard if on dashboard page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the dashboard page
    if (document.getElementById('stats-grid')) {
        fetchStats();
    }
    
    // Initialize QR scanner if we're on the scan page
    if (document.getElementById('qr-reader')) {
        initQRScanner();
    }
    
    // Handle QR code scanning from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('t');
    if (token && window.location.pathname === '/scan') {
        // Token is handled by the Flask template, but we can store it for JS use
        teamToken = token;
    }
});

// Service worker registration for offline capability (optional enhancement)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Only register if we have a service worker file
        fetch('/sw.js', { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    navigator.serviceWorker.register('/sw.js')
                        .then(registration => {
                            console.log('ServiceWorker registered');
                        })
                        .catch(error => {
                            console.log('ServiceWorker registration failed');
                        });
                }
            })
            .catch(() => {
                // Service worker file doesn't exist, skip registration
            });
    });
}

// Handle keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + K to open manual scan
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        openManualScan();
    }
    
    // Escape to close modal
    if (event.key === 'Escape') {
        closeManualScan();
    }
    
    // F5 or Ctrl/Cmd + R to refresh stats on dashboard
    if ((event.key === 'F5' || ((event.ctrlKey || event.metaKey) && event.key === 'r')) 
        && document.getElementById('stats-grid')) {
        event.preventDefault();
        fetchStats();
    }
});

// Export functions for global access (if needed)
window.hackathonAttendance = {
    openManualScan,
    closeManualScan,
    manualScan,
    teamAction,
    memberAction,
    fetchStats,
    filterTeams,
    showNotification
};