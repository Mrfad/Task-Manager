document.addEventListener('DOMContentLoaded', function () {
    const clearTaskBtn = document.getElementById('clear-notifications-btn');
    const clearPaymentBtn = document.getElementById('clear-payment-notifications-btn');

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    if (clearTaskBtn) {
        clearTaskBtn.addEventListener('click', function () {
            const url = clearTaskBtn.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('notification-dropdown').innerHTML =
                        '<li class="dropdown-item text-wrap">No new notifications</li>';
                    document.getElementById('notification-badge').classList.add('d-none');
                }
            });
        });
    }

    if (clearPaymentBtn) {
        clearPaymentBtn.addEventListener('click', function () {
            const url = clearPaymentBtn.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('payment-notification-dropdown').innerHTML =
                        '<li class="dropdown-item text-wrap">No new payment notifications</li>';
                    document.getElementById('payment-notification-badge').classList.add('d-none');
                }
            });
        });
    }
});

