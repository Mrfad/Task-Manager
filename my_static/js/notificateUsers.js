const socket = new WebSocket(`ws://${window.location.host}/ws/notifications/`);

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const taskId = data.task_id || "#";
    const taskTitle = data.task_title || "New Task";
    const createdBy = data.created_by || "System";
    const dueDate = data.due_date || "";
    const category = data.category || "task"; // <-- NEW LINE
    const link = `/task/detail/${taskId}/`;

    const li = document.createElement('li');
    li.className = '';
    li.innerHTML = `
        <a href="${link}" class="dropdown-item text-wrap">
            ${data.message}
        </a>`;

    if (category === "payment") {
        const badge = document.getElementById('payment-notification-badge');
        const dropdown = document.getElementById('payment-notification-dropdown');
        if (badge) {
            let count = parseInt(badge.textContent.trim()) || 0;
            badge.textContent = count + 1;
            badge.classList.remove('d-none');
        }
        if (dropdown) {
            const emptyItem = dropdown.querySelector('.dropdown-item');
            if (emptyItem && emptyItem.textContent.includes('No new')) {
                dropdown.removeChild(emptyItem);
            }
            dropdown.prepend(li);
        }
    } else {
        const badge = document.getElementById('notification-badge');
        const dropdown = document.getElementById('notification-dropdown');
        if (badge) {
            let count = parseInt(badge.textContent.trim()) || 0;
            badge.textContent = count + 1;
            badge.classList.remove('d-none');
        }
        if (dropdown) {
            const emptyItem = dropdown.querySelector('.dropdown-item');
            if (emptyItem && emptyItem.textContent.includes('No new')) {
                dropdown.removeChild(emptyItem);
            }
            dropdown.prepend(li);
        }
    }

    showToast(link, data.message, createdBy, dueDate, category);
}

function showToast(taskUrl, message, createdBy, dueDate, category) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast show custom-toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    const emoji = category === "payment" ? "💰" : "🔔";

    toast.innerHTML = `
        <div class="d-flex">
            <a href="${taskUrl}" class="toast-body bg-warning text-dark w-100 text-decoration-none">
                <div class="fs-5 fw-bold">${emoji} ${message}</div>
                ${dueDate ? `<div class="fs-6">By: ${createdBy} &bull; Due: ${dueDate}</div>` : `<div class="fs-6">By: ${createdBy}</div>`}
            </a>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toast);
    new bootstrap.Toast(toast, { delay: 7000 }).show();

    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}
