(function initStudentDashboard() {
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

    function getCameraBlockReason() {
        if (!window.isSecureContext) {
            return 'Camera is blocked because this page is not running on HTTPS (or localhost). Open the app over HTTPS.';
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return 'Camera API is not available in this browser.';
        }
        return '';
    }

    function setup() {
        updateClock();
        setInterval(updateClock, 1000);

        const config = document.getElementById('studentDashboardConfig');
        if (!config) {
            return;
        }

        const scanUrl = config.dataset.scanUrl;
        const registerUrl = config.dataset.registerUrl;
        const verifyUrl = config.dataset.verifyUrl;
        let faceVerified = config.dataset.faceVerified === 'true';
        let cameraMode = 'register';
        let pendingAttendanceId = null;
        let selectedClassroomId = null;
        let stream = null;
        let qrScanner = null;
        let scannerRunning = false;

        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const captureBtn = document.getElementById('captureBtn');
        const faceRegisterBtn = document.getElementById('faceRegisterBtn');
        const cameraStatus = document.getElementById('cameraStatus');
        const cameraModalElement = document.getElementById('cameraModal');
        const cameraModalLabel = document.getElementById('cameraModalLabel');

        const scanModalElement = document.getElementById('scanQrModal');
        const scanStatus = document.getElementById('scanStatus');
        const manualTokenInput = document.getElementById('manualTokenInput');
        const manualTokenSubmitBtn = document.getElementById('manualTokenSubmitBtn');

        if (
            !video || !canvas || !captureBtn || !faceRegisterBtn || !cameraStatus || !cameraModalElement ||
            !cameraModalLabel || !scanModalElement || !scanStatus || !manualTokenInput || !manualTokenSubmitBtn
        ) {
            return;
        }

        let scanModal = null;
        let cameraModal = null;
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            cameraModal = new bootstrap.Modal(cameraModalElement);
            scanModal = new bootstrap.Modal(scanModalElement);
        }

        function setCameraMode(mode) {
            cameraMode = mode;
            if (mode === 'attendance') {
                cameraModalLabel.textContent = 'Verify Face for Attendance';
                captureBtn.textContent = 'Verify Face';
            } else {
                cameraModalLabel.textContent = 'Register Facial Biometrics';
                captureBtn.textContent = 'Capture Photo';
            }
        }

        function startCamera() {
            const reason = getCameraBlockReason();
            if (reason) {
                cameraStatus.innerHTML = `<span class="text-danger">${reason}</span>`;
                return;
            }
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
                .then(function (mediaStream) {
                    stream = mediaStream;
                    video.srcObject = stream;
                    cameraStatus.innerHTML = '<span class="text-success">Camera ready. Position your face in the frame.</span>';
                })
                .catch(function () {
                    cameraStatus.innerHTML = '<span class="text-danger">Error accessing camera. Please allow camera permissions.</span>';
                });
        }

        async function stopScanner() {
            if (qrScanner && scannerRunning) {
                try {
                    await qrScanner.stop();
                } catch (err) {
                    // no-op
                }
                try {
                    await qrScanner.clear();
                } catch (err) {
                    // no-op
                }
            }
            scannerRunning = false;
        }

        async function submitScannedToken(tokenText) {
            const token = (tokenText || '').trim();
            if (!token) {
                scanStatus.innerHTML = '<span class="text-danger">Token cannot be empty.</span>';
                return;
            }

            scanStatus.innerHTML = '<span class="text-info">Validating QR...</span>';
            try {
                const response = await fetch(scanUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        token: token,
                        classroom_id: selectedClassroomId,
                    }),
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    if (data.error === "You don't belong to this class.") {
                        alert("You don't belong to this class.");
                    }
                    scanStatus.innerHTML = `<span class="text-danger">${data.error || 'QR scan failed.'}</span>`;
                    return;
                }

                pendingAttendanceId = data.attendance_id;
                scanStatus.innerHTML = '<span class="text-success">QR accepted. Starting face verification...</span>';
                setTimeout(function () {
                    if (scanModal) {
                        scanModal.hide();
                    }
                    setCameraMode('attendance');
                    if (cameraModal) {
                        cameraModal.show();
                        setTimeout(startCamera, 250);
                    }
                }, 600);
            } catch (err) {
                scanStatus.innerHTML = '<span class="text-danger">Network error while validating QR.</span>';
            }
        }

        async function startScanner() {
            scanStatus.innerHTML = '<span class="text-muted">Point camera at teacher QR code.</span>';
            const reason = getCameraBlockReason();
            if (reason) {
                scanStatus.innerHTML = `<span class="text-danger">${reason}</span>`;
                return;
            }
            if (typeof Html5Qrcode === 'undefined') {
                scanStatus.innerHTML = '<span class="text-danger">QR scanner library failed to load. Please refresh and try again.</span>';
                return;
            }

            await stopScanner();
            qrScanner = new Html5Qrcode('qr-reader');
            scannerRunning = true;
            try {
                await qrScanner.start(
                    { facingMode: 'environment' },
                    { fps: 10, qrbox: { width: 220, height: 220 } },
                    async function onScanSuccess(decodedText) {
                        await stopScanner();
                        submitScannedToken(decodedText);
                    },
                    function onScanFailure() {}
                );
            } catch (err) {
                scanStatus.innerHTML = '<span class="text-danger">Unable to start QR scanner.</span>';
                scannerRunning = false;
            }
        }

        document.querySelectorAll('.mark-attendance-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (!faceVerified) {
                    alert('Please register facial biometrics first.');
                    return;
                }
                selectedClassroomId = parseInt(btn.dataset.classroomId, 10);
                if (scanModal) {
                    scanModal.show();
                    setTimeout(startScanner, 300);
                }
            });
        });

        manualTokenSubmitBtn.addEventListener('click', async function () {
            await stopScanner();
            submitScannedToken(manualTokenInput.value);
        });

        manualTokenInput.addEventListener('keydown', async function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                await stopScanner();
                submitScannedToken(manualTokenInput.value);
            }
        });

        faceRegisterBtn.addEventListener('click', function (event) {
            event.preventDefault();
            if (faceVerified) {
                alert('Your face is already verified!');
                return;
            }
            setCameraMode('register');
            if (cameraModal) {
                cameraModal.show();
                setTimeout(startCamera, 250);
            }
        });

        scanModalElement.addEventListener('hidden.bs.modal', function () {
            stopScanner();
            scanStatus.innerHTML = '';
            manualTokenInput.value = '';
        });

        cameraModalElement.addEventListener('hidden.bs.modal', function () {
            if (stream) {
                stream.getTracks().forEach(function (track) {
                    track.stop();
                });
                stream = null;
            }
            video.srcObject = null;
            cameraStatus.innerHTML = '';
            captureBtn.disabled = false;
            setCameraMode('register');
            pendingAttendanceId = null;
        });

        captureBtn.addEventListener('click', async function () {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            const imageData = canvas.toDataURL('image/png');

            captureBtn.disabled = true;
            cameraStatus.innerHTML = '<div class="alert alert-info"><strong>Processing...</strong></div>';

            let url = registerUrl;
            let payload = { image: imageData };
            if (cameraMode === 'attendance') {
                if (!pendingAttendanceId) {
                    cameraStatus.innerHTML = '<span class="text-danger">Missing attendance context. Scan QR again.</span>';
                    captureBtn.disabled = false;
                    return;
                }
                url = verifyUrl;
                payload = { image: imageData, attendance_id: pendingAttendanceId };
            }

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok || (!data.success && data.match !== false)) {
                    throw new Error(data.error || 'Request failed');
                }

                if (cameraMode === 'register') {
                    if (data.success) {
                        faceVerified = true;
                        faceRegisterBtn.textContent = 'Face Verified';
                        faceRegisterBtn.classList.remove('btn-primary');
                        faceRegisterBtn.classList.add('btn-success');
                        cameraStatus.innerHTML = '<span class="text-success">Face registered successfully!</span>';
                        setTimeout(function () {
                            window.location.reload();
                        }, 900);
                    }
                } else {
                    if (data.match) {
                        cameraStatus.innerHTML = `<span class="text-success">Attendance marked. Score: ${Number(data.score).toFixed(4)}</span>`;
                    } else {
                        cameraStatus.innerHTML = `<span class="text-danger">Face verification failed. Score: ${Number(data.score).toFixed(4)}</span>`;
                    }
                    setTimeout(function () {
                        if (cameraModal) {
                            cameraModal.hide();
                        }
                    }, 1200);
                }
            } catch (err) {
                cameraStatus.innerHTML = `<span class="text-danger">${err.message}</span>`;
                captureBtn.disabled = false;
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();
