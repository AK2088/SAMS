(function initTeacherDashboard() {
    function updateClock() {
        const clock = document.getElementById('clock');
        if (!clock) {
            return;
        }
        const now = new Date();
        const options = {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: 'Asia/Kolkata',
        };
        clock.innerText = now.toLocaleString('en-IN', options);
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i += 1) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === `${name}=`) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function buildUrl(template, id) {
        return template.replace(/0\/?$/, `${id}/`);
    }

    function sanitizeFilename(name) {
        const cleaned = (name || '')
            .replace(/[\\/:*?"<>|]+/g, '')
            .replace(/\s+/g, ' ')
            .trim();
        return cleaned || 'attendance';
    }

    function setup() {
        updateClock();
        setInterval(updateClock, 1000);

        const config = document.getElementById('teacherDashboardConfig');
        if (!config) {
            return;
        }

        const startTemplate = config.dataset.startTemplate;
        const qrTemplate = config.dataset.qrTemplate;
        const stopTemplate = config.dataset.stopTemplate;
        const downloadTemplate = config.dataset.downloadTemplate;

        const qrModalEl = document.getElementById('qrModal');
        const qrCanvas = document.getElementById('qrCanvas');
        const qrStatus = document.getElementById('qrStatus');
        const qrExpiry = document.getElementById('qrExpiry');
        const qrTokenText = document.getElementById('qrTokenText');
        const qrInlinePanel = document.getElementById('qrInlinePanel');
        const qrCanvasInline = document.getElementById('qrCanvasInline');
        const qrStatusInline = document.getElementById('qrStatusInline');
        const qrExpiryInline = document.getElementById('qrExpiryInline');
        const qrTokenTextInline = document.getElementById('qrTokenTextInline');
        const stopBtn = document.getElementById('stopSessionBtn');
        const stopBtnInline = document.getElementById('stopSessionBtnInline');

        if (
            !qrModalEl || !qrCanvas || !qrStatus || !qrExpiry || !qrTokenText || !qrInlinePanel ||
            !qrCanvasInline || !qrStatusInline || !qrExpiryInline || !qrTokenTextInline || !stopBtn || !stopBtnInline
        ) {
            return;
        }

        let qrModal = null;
        let sessionId = null;
        let pollTimer = null;
        let countdownTimer = null;
        let expiresAtMs = null;
        let isStopping = false;

        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            qrModal = new bootstrap.Modal(qrModalEl);
        }

        function setStatus(msg, isError) {
            const cssClass = isError ? 'text-danger' : 'text-success';
            qrStatus.innerHTML = `<span class="${cssClass}">${msg}</span>`;
            qrStatusInline.innerHTML = `<span class="${cssClass}">${msg}</span>`;
        }

        function renderQr(token) {
            qrTokenText.textContent = token;
            qrTokenTextInline.textContent = token;
            if (!window.QRCode || !QRCode.toCanvas) {
                setStatus('QR library failed to load.', true);
                return;
            }
            QRCode.toCanvas(qrCanvas, token, { width: 250 }, function (error) {
                if (error) {
                    setStatus('Failed to render QR.', true);
                }
            });
            QRCode.toCanvas(qrCanvasInline, token, { width: 250 }, function (error) {
                if (error) {
                    setStatus('Failed to render QR.', true);
                }
            });
        }

        function startCountdown() {
            clearInterval(countdownTimer);
            countdownTimer = setInterval(function () {
                if (!expiresAtMs) {
                    qrExpiry.textContent = '';
                    qrExpiryInline.textContent = '';
                    return;
                }
                const left = Math.max(0, Math.ceil((expiresAtMs - Date.now()) / 1000));
                qrExpiry.textContent = `Expires in ${left}s`;
                qrExpiryInline.textContent = `Expires in ${left}s`;
            }, 500);
        }

        function stopTimers() {
            clearInterval(pollTimer);
            clearInterval(countdownTimer);
            pollTimer = null;
            countdownTimer = null;
            expiresAtMs = null;
        }

        function clearQrDisplay() {
            qrStatus.innerHTML = '';
            qrStatusInline.innerHTML = '';
            qrExpiry.textContent = '';
            qrExpiryInline.textContent = '';
            qrTokenText.textContent = '';
            qrTokenTextInline.textContent = '';
            const ctxMain = qrCanvas.getContext('2d');
            ctxMain.clearRect(0, 0, qrCanvas.width, qrCanvas.height);
            const ctxInline = qrCanvasInline.getContext('2d');
            ctxInline.clearRect(0, 0, qrCanvasInline.width, qrCanvasInline.height);
        }

        function closeQrModalUi() {
            // Preferred close path via Bootstrap API.
            if (qrModal && typeof qrModal.hide === 'function') {
                qrModal.hide();
                return;
            }

            // Fallback close path for stale/bootstrap edge cases.
            qrModalEl.classList.remove('show');
            qrModalEl.style.display = 'none';
            qrModalEl.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
            document.querySelectorAll('.modal-backdrop').forEach(function (el) {
                el.remove();
            });
        }

        async function refreshQr() {
            if (!sessionId) {
                return;
            }
            try {
                const response = await fetch(buildUrl(qrTemplate, sessionId));
                const data = await response.json();
                if (!response.ok || !data.success) {
                    setStatus(data.error || 'Failed to refresh QR.', true);
                    return;
                }
                renderQr(data.token);
                expiresAtMs = new Date(data.expires_at).getTime();
                startCountdown();
                setStatus('QR updated.', false);
            } catch (err) {
                setStatus('Network error while refreshing QR.', true);
            }
        }

        document.querySelectorAll('.take-attendance-btn').forEach(function (btn) {
            btn.addEventListener('click', async function () {
                const classroomId = btn.dataset.classroomId;
                btn.disabled = true;
                try {
                    const response = await fetch(buildUrl(startTemplate, classroomId), {
                        method: 'POST',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                    });
                    const data = await response.json();
                    if (!response.ok || !data.success) {
                        alert(data.error || 'Could not start attendance.');
                        return;
                    }

                    stopTimers();
                    sessionId = data.session_id;
                    renderQr(data.token);
                    expiresAtMs = new Date(data.expires_at).getTime();
                    startCountdown();
                    setStatus('Session started.', false);
                    qrInlinePanel.style.display = 'block';
                    qrInlinePanel.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    if (qrModal) {
                        qrModal.show();
                    }
                    pollTimer = setInterval(refreshQr, 3000);
                } catch (err) {
                    alert('Network error while starting attendance.');
                } finally {
                    btn.disabled = false;
                }
            });
        });

        document.querySelectorAll('.download-attendance-btn').forEach(function (btn) {
            btn.addEventListener('click', async function () {
                const classroomId = btn.dataset.classroomId;
                const downloadName = sanitizeFilename(btn.dataset.downloadName || `attendance_${classroomId}`);
                btn.disabled = true;
                try {
                    const response = await fetch(buildUrl(downloadTemplate, classroomId));
                    const contentType = response.headers.get('content-type') || '';

                    if (!response.ok || contentType.includes('application/json')) {
                        const data = await response.json().catch(function () {
                            return {};
                        });
                        alert(data.error || 'Unable to download attendance right now.');
                        return;
                    }

                    const blob = await response.blob();
                    const fileUrl = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = fileUrl;
                    link.download = `${downloadName}.xls`;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    window.URL.revokeObjectURL(fileUrl);
                } catch (err) {
                    alert('Network error while downloading attendance.');
                } finally {
                    btn.disabled = false;
                }
            });
        });

        async function stopCurrentSession() {
            if (!sessionId) {
                return true;
            }
            if (isStopping) {
                return false;
            }
            isStopping = true;
            // Stop polling immediately so no additional tokens are requested.
            stopTimers();
            const activeSessionId = sessionId;
            try {
                const response = await fetch(buildUrl(stopTemplate, activeSessionId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    setStatus(data.error || 'Failed to stop session.', true);
                    sessionId = activeSessionId;
                    return false;
                }
                setStatus('Session stopped.', false);
                qrInlinePanel.style.display = 'none';
                sessionId = null;
                clearQrDisplay();
                return true;
            } catch (err) {
                setStatus('Network error while stopping session.', true);
                sessionId = activeSessionId;
                return false;
            } finally {
                isStopping = false;
            }
        }

        stopBtn.addEventListener('click', async function () {
            stopBtn.disabled = true;
            const stopped = await stopCurrentSession();
            if (stopped) {
                closeQrModalUi();
            }
            stopBtn.disabled = false;
        });
        stopBtnInline.addEventListener('click', stopCurrentSession);

        qrModalEl.addEventListener('hidden.bs.modal', function () {
            // Closing modal is treated as ending attendance for this session.
            if (sessionId) {
                stopCurrentSession();
            } else {
                clearQrDisplay();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();
