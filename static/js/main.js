// Main JavaScript file for global functionality

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        if (!alert.classList.contains('alert-important')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
});

// Confirmation for delete actions
function confirmDelete(message = 'Are you sure you want to delete this?') {
    return confirm(message);
}

// Format date to readable format
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format time
function formatTime(timeString) {
    return new Date('1970-01-01T' + timeString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Show loading spinner
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'globalLoading';
    loadingDiv.className = 'position-fixed top-50 start-50 translate-middle';
    loadingDiv.innerHTML = `
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(loadingDiv);
}

// Hide loading spinner
function hideLoading() {
    const loadingDiv = document.getElementById('globalLoading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Toast notification
function showToast(message, type = 'success') {
    const toastDiv = document.createElement('div');
    toastDiv.className = `position-fixed bottom-0 end-0 p-3`;
    toastDiv.style.zIndex = '11';
    toastDiv.innerHTML = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    document.body.appendChild(toastDiv);
    const toast = new bootstrap.Toast(toastDiv.querySelector('.toast'));
    toast.show();

    // Remove after hiding
    toastDiv.querySelector('.toast').addEventListener('hidden.bs.toast', () => {
        toastDiv.remove();
    });
}
