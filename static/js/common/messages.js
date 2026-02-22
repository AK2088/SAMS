(function initDjangoMessages() {
    function showMessages() {
        const store = document.getElementById('django-message-store');
        if (!store) {
            return;
        }

        const items = store.querySelectorAll('.django-message-item');
        items.forEach((item) => {
            const message = item.dataset.message;
            if (message) {
                alert(message);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showMessages);
    } else {
        showMessages();
    }
})();
