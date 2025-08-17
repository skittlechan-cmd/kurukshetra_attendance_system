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

window.openScanOptions = function() {
    document.getElementById('scan-modal').style.display = 'block';
};

window.closeScanModal = function() {
    document.getElementById('scan-modal').style.display = 'none';
};

window.openManualEntry = function() {
    window.closeScanModal();
    document.getElementById('manual-entry-modal').style.display = 'block';
};

window.closeManualEntry = function() {
    document.getElementById('manual-entry-modal').style.display = 'none';
    document.getElementById('manual-token').value = '';
};

window.manualScan = function() {
    const token = document.getElementById('manual-token').value.trim();
    if (!token) {
        showNotification('Please enter a token', 'error');
        return;
    }
    window.location.href = `/scan?t=${encodeURIComponent(token)}`;
};

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup modal close on outside click
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });

    // Handle Enter key in manual token input
    const manualTokenInput = document.getElementById('manual-token');
    if (manualTokenInput) {
        manualTokenInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                window.manualScan();
            }
        });
    }

    // Setup mobile navigation
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        navMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
    }
});
