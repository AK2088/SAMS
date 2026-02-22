(function initRoleToggles() {
    function applyToggle(selectEl) {
        if (!selectEl) {
            return;
        }

        const studentTargetId = selectEl.dataset.studentTarget;
        const facultyTargetId = selectEl.dataset.facultyTarget;
        const studentTarget = document.getElementById(studentTargetId);
        const facultyTarget = document.getElementById(facultyTargetId);
        const role = selectEl.value;

        if (!studentTarget || !facultyTarget) {
            return;
        }

        if (role === 'student') {
            studentTarget.classList.remove('d-none');
            facultyTarget.classList.add('d-none');
        } else {
            studentTarget.classList.add('d-none');
            facultyTarget.classList.remove('d-none');
        }
    }

    function setup() {
        const selects = document.querySelectorAll('[data-role-toggle]');
        selects.forEach((selectEl) => {
            selectEl.addEventListener('change', function () {
                applyToggle(selectEl);
            });
            applyToggle(selectEl);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();
