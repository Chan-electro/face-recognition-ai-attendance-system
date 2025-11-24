// Camera handling for face recognition attendance
let videoElement, canvasElement, stream;

document.addEventListener('DOMContentLoaded', function () {
    videoElement = document.getElementById('videoElement');
    canvasElement = document.getElementById('canvasElement');
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    const stopBtn = document.getElementById('stopCameraBtn');
    const placeholderImage = document.getElementById('placeholderImage');

    if (startBtn) {
        startBtn.addEventListener('click', startCamera);
    }

    if (captureBtn) {
        captureBtn.addEventListener('click', captureAndRecognize);
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', stopCamera);
    }
});

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 }
            }
        });

        videoElement.srcObject = stream;

        // Show/hide elements
        document.getElementById('placeholderImage').style.display = 'none';
        videoElement.style.display = 'block';
        document.getElementById('startCameraBtn').style.display = 'none';
        document.getElementById('captureBtn').style.display = 'block';
        document.getElementById('stopCameraBtn').style.display = 'block';

    } catch (error) {
        console.error('Error accessing camera:', error);
        showResult('error', 'Failed to access camera. Please check permissions.');
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        videoElement.srcObject = null;
    }

    // Reset UI
    videoElement.style.display = 'none';
    canvasElement.style.display = 'none';
    document.getElementById('placeholderImage').style.display = 'block';
    document.getElementById('startCameraBtn').style.display = 'block';
    document.getElementById('captureBtn').style.display = 'none';
    document.getElementById('stopCameraBtn').style.display = 'none';
    document.getElementById('resultArea').innerHTML = '';
}

async function captureAndRecognize() {
    const subjectId = document.getElementById('subjectSelect').value;

    if (!subjectId) {
        showResult('warning', 'Please select a subject first');
        return;
    }

    // Capture frame from video
    const context = canvasElement.getContext('2d');
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    context.drawImage(videoElement, 0, 0);

    // Convert to base64
    const imageData = canvasElement.toDataURL('image/jpeg', 0.8);

    // Show loading
    showResult('info', 'Recognizing face... <div class="spinner-border spinner-border-sm ms-2" role="status"></div>');

    try {
        const response = await fetch('/teacher/mark-attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageData,
                subject_id: parseInt(subjectId)
            })
        });

        const result = await response.json();

        if (result.success) {
            showResult('success', `
                <i class="material-icons align-middle">check_circle</i>
                <strong>Success!</strong> Attendance marked for ${result.student.full_name}
                <br><small>Confidence: ${(result.confidence * 100).toFixed(2)}%</small>
            `);

            // Play success sound (optional)
            playSuccessSound();
        } else {
            showResult('danger', `
                <i class="material-icons align-middle">error</i>
                <strong>Failed:</strong> ${result.message}
            `);
        }
    } catch (error) {
        console.error('Error:', error);
        showResult('danger', 'Network error occurred. Please try again.');
    }
}

function showResult(type, message) {
    const resultArea = document.getElementById('resultArea');
    resultArea.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

function playSuccessSound() {
    // Optional: Add a success beep
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
}
