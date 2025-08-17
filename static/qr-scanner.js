// QR Scanner functionality
class QRScanner {
    constructor() {
        this.html5QrCode = null;
        this.currentCamera = null;
        this.scanning = false;
    }

    async start() {
        const qrReader = document.getElementById('qr-reader');
        if (!qrReader) return;

        try {
            // Request camera permissions first
            await this.requestCameraPermission();

            // Initialize scanner
            this.html5QrCode = new Html5Qrcode("qr-reader");
            
            // Get available cameras
            const cameras = await this.getCameras();
            if (cameras.length === 0) {
                throw new Error('No cameras found');
            }

            // Select the best camera (prefer back camera)
            const camera = cameras.find(c => 
                c.label.toLowerCase().includes('back') || 
                c.label.toLowerCase().includes('rear')
            ) || cameras[0];

            // Start scanning
            await this.html5QrCode.start(
                camera.deviceId,
                {
                    fps: 10,
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0
                },
                (decodedText) => {
                    this.stop();
                    window.location.href = `/scan?t=${encodeURIComponent(decodedText)}`;
                },
                () => {} // Ignore errors during scanning
            );

            this.currentCamera = camera;
            this.scanning = true;

        } catch (error) {
            console.error('QR Scanner error:', error);
            qrReader.innerHTML = this.getErrorHTML(error);
        }
    }

    async stop() {
        if (this.html5QrCode && this.scanning) {
            try {
                await this.html5QrCode.stop();
                this.scanning = false;
            } catch (error) {
                console.error('Error stopping scanner:', error);
            }
        }
    }

    async requestCameraPermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
        } catch (error) {
            throw new Error('Camera permission denied. Please allow camera access.');
        }
    }

    async getCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.filter(device => device.kind === 'videoinput');
        } catch (error) {
            throw new Error('Failed to enumerate cameras');
        }
    }

    getErrorHTML(error) {
        return `
            <div class="camera-permission-error">
                <p>⚠️ Camera Error</p>
                <p class="error-details">${error.message}</p>
                <div class="troubleshooting-steps">
                    <p><strong>Please try these steps:</strong></p>
                    <ol>
                        <li>Make sure your camera is not being used by another application</li>
                        <li>Allow camera access when prompted by your browser</li>
                        <li>Refresh the page and try again</li>
                        <li>Try using a different browser</li>
                    </ol>
                </div>
                <div class="action-buttons">
                    <button onclick="qrScanner.start()" class="btn-primary">Try Again</button>
                    <button onclick="openManualEntry()" class="btn-secondary">Manual Entry</button>
                </div>
            </div>
        `;
    }
}

// Initialize QR Scanner
const qrScanner = new QRScanner();

// Update the startQRScanner function to use our new class
async function startQRScanner() {
    closeScanModal();
    document.getElementById('qr-scanner-modal').style.display = 'block';
    document.getElementById('qr-reader').innerHTML = ''; // Clear previous content
    await qrScanner.start();
}

function closeQRScanner() {
    const modal = document.getElementById('qr-scanner-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    qrScanner.stop();
}
