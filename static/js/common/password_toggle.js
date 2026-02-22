(function initPasswordToggles() {
    function addToggle(input) {
        if (!input || input.dataset.toggleReady === '1') {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'position-relative';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        input.classList.add('pe-5');
        input.dataset.toggleReady = '1';

        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'btn btn-outline-secondary btn-sm position-absolute top-50 end-0 translate-middle-y me-2 px-2 py-0 password-toggle-btn';
        toggleBtn.textContent = 'Show';
        toggleBtn.setAttribute('aria-label', 'Show password');

        toggleBtn.addEventListener('click', function () {
            const isHidden = input.type === 'password';
            input.type = isHidden ? 'text' : 'password';
            toggleBtn.textContent = isHidden ? 'Hide' : 'Show';
            toggleBtn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
        });

        wrapper.appendChild(toggleBtn);
    }

    function setup() {
        document.querySelectorAll('input[type="password"]').forEach(addToggle);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();
