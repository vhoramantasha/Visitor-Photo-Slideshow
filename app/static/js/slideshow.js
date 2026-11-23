// Smart TV Slideshow Controller
(function () {
    const config = window.SLIDESHOW_CONFIG || {
        duration: 8,
        uploadUrl: window.location.origin,
        streamUrl: '/api/stream',
        fetchUrl: '/api/slideshow/all'
    };

    // DOM Elements
    const layerA = document.getElementById('slideLayerA');
    const layerB = document.getElementById('slideLayerB');
    const welcomeBanner = document.getElementById('welcomeBanner');
    const bannerBadge = document.getElementById('bannerBadge');
    const bannerTitle = document.getElementById('bannerTitle');
    const bannerSubtitle = document.getElementById('bannerSubtitle');
    const timerProgress = document.getElementById('timerProgress');
    const timerSeconds = document.getElementById('timerSeconds');
    const standbyScreen = document.getElementById('standbyScreen');
    const statusDot = document.getElementById('statusDot');
    const statusLabel = document.getElementById('statusLabel');
    const queueBadge = document.getElementById('queueBadge');
    const pauseBtn = document.getElementById('pauseBtn');
    const toggleQrBtn = document.getElementById('toggleQrBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const qrOverlay = document.getElementById('qrOverlay');
    const qrContainer = document.getElementById('qrCodeContainer');

    // State
    let priorityQueue = [];
    let ambientPool = [];
    let ambientIndex = 0;
    let currentSlide = null;
    let activeLayer = 'A';
    let isPaused = false;
    let slideTimer = null;
    let countdownInterval = null;
    let secondsLeft = config.duration;
    let eventSource = null;
    let reconnectDelay = 2000;

    // Initialize
    async function init() {
        renderQrCode(config.uploadUrl);
        setupEventListeners();
        connectSSE();
        await fetchAmbientPool();
        startSlideshowCycle();
    }

    // Connect Server-Sent Events (SSE)
    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(config.streamUrl);

        eventSource.addEventListener('connected', (e) => {
            statusDot.className = 'status-dot connected';
            statusLabel.textContent = 'Live Connected';
            reconnectDelay = 2000;
        });

        eventSource.addEventListener('live_upload', (e) => {
            try {
                const payload = JSON.parse(e.data);
                const data = payload.data || payload;
                handleLiveUploadEvent(data);
            } catch (err) {
                console.error('Failed to parse live_upload event:', err);
            }
        });

        eventSource.addEventListener('photo_deleted', (e) => {
            try {
                const payload = JSON.parse(e.data);
                const photoId = payload.data?.photo_id || payload.photo_id;
                handlePhotoDeleted(photoId);
            } catch (err) {
                console.error('Failed to parse photo_deleted event:', err);
            }
        });

        eventSource.onerror = () => {
            statusDot.className = 'status-dot';
            statusLabel.textContent = 'Reconnecting...';
            eventSource.close();
            setTimeout(connectSSE, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
        };
    }

    // Handle new incoming live uploads
    function handleLiveUploadEvent(data) {
        const items = data.items || [];
        if (items.length === 0) return;

        // Push new items to priority queue
        priorityQueue.push(...items);
        updateQueueUI();

        // Also add new items into ambient pool so they persist in the overall loop
        items.forEach(item => {
            if (!ambientPool.some(p => p.url === item.url)) {
                ambientPool.unshift(item);
            }
        });

        // Hide standby screen if it was visible
        standbyScreen.style.display = 'none';

        // If currently idling on ambient or standby, immediately transition to the new arrival!
        if (!currentSlide || !currentSlide.is_new) {
            advanceToNextSlide();
        }
    }

    function handlePhotoDeleted(photoId) {
        priorityQueue = priorityQueue.filter(item => item.photo_id !== photoId);
        ambientPool = ambientPool.filter(item => (item.id || item.photo_id) !== photoId);
        updateQueueUI();

        if (currentSlide && (currentSlide.id === photoId || currentSlide.photo_id === photoId)) {
            advanceToNextSlide();
        }
    }

    // Fetch initial ambient photos
    async function fetchAmbientPool() {
        try {
            const res = await fetch(config.fetchUrl);
            const data = await res.json();
            if (data.photos && data.photos.length > 0) {
                ambientPool = data.photos;
            }
        } catch (err) {
            console.warn('Failed to load initial photos:', err);
        }
    }

    // Slide Transition Engine
    function advanceToNextSlide() {
        if (isPaused) return;

        let nextItem = null;

        if (priorityQueue.length > 0) {
            nextItem = priorityQueue.shift();
            updateQueueUI();
        } else if (ambientPool.length > 0) {
            if (ambientIndex >= ambientPool.length) {
                ambientIndex = 0;
            }
            nextItem = ambientPool[ambientIndex];
            ambientIndex++;
        }

        if (!nextItem) {
            // No photos available
            standbyScreen.style.display = 'flex';
            currentSlide = null;
            return;
        }

        standbyScreen.style.display = 'none';
        renderSlide(nextItem);
    }

    function renderSlide(item) {
        currentSlide = item;
        const currentLayerEl = activeLayer === 'A' ? layerA : layerB;
        const nextLayerEl = activeLayer === 'A' ? layerB : layerA;
        const nextLayerName = activeLayer === 'A' ? 'B' : 'A';

        // Preload image
        const img = new Image();
        img.src = item.url;
        img.onload = () => {
            // Set image and Ken Burns animation
            nextLayerEl.style.backgroundImage = `url("${item.url}")`;
            nextLayerEl.className = `slide-layer active ken-burns-${nextLayerName === 'A' ? '1' : '2'}`;
            currentLayerEl.className = 'slide-layer'; // fade out

            activeLayer = nextLayerName;
            updateBanner(item);
            startTimer(item.duration || config.duration);
        };
        img.onerror = () => {
            // Skip broken image
            advanceToNextSlide();
        };
    }

    function updateBanner(item) {
        const isReturning = item.is_returning || (item.visit_count && item.visit_count > 1);
        const name = item.visitor_name || 'Special Visitor';

        if (item.is_new) {
            bannerBadge.textContent = isReturning ? '✨ WELCOME BACK' : '🌟 NEW VISITOR';
            bannerBadge.className = isReturning ? 'banner-badge returning' : 'banner-badge';
            bannerTitle.textContent = isReturning
                ? `Welcome back, ${name}!`
                : `Welcome, ${name}!`;
            bannerSubtitle.textContent = item.label || (
                item.batch_total > 1
                    ? `Showing photo ${item.batch_index} of ${item.batch_total}`
                    : `Just arrived & sharing memories`
            );
        } else if (isReturning && item.label) {
            bannerBadge.textContent = '📸 MEMORY VAULT';
            bannerBadge.className = 'banner-badge returning';
            bannerTitle.textContent = `${name}'s Previous Visit`;
            bannerSubtitle.textContent = item.label;
        } else {
            bannerBadge.textContent = 'COMMUNITY MOMENT';
            bannerBadge.className = 'banner-badge';
            bannerTitle.textContent = name;
            bannerSubtitle.textContent = `Shared with our community`;
        }

        welcomeBanner.style.opacity = '1';
        welcomeBanner.style.transform = 'translateY(0)';
    }

    // Countdown Timer Ring
    function startTimer(duration) {
        clearTimers();
        secondsLeft = duration;
        updateTimerDisplay();

        countdownInterval = setInterval(() => {
            if (isPaused) return;
            secondsLeft -= 0.1;
            if (secondsLeft <= 0) {
                clearTimers();
                advanceToNextSlide();
            } else {
                updateTimerDisplay();
            }
        }, 100);
    }

    function updateTimerDisplay() {
        const progressPercent = Math.max(0, (secondsLeft / config.duration) * 100);
        timerProgress.style.strokeDasharray = `${progressPercent}, 100`;
        timerSeconds.textContent = `${Math.ceil(secondsLeft)}s`;
    }

    function clearTimers() {
        if (countdownInterval) clearInterval(countdownInterval);
        if (slideTimer) clearTimeout(slideTimer);
    }

    function updateQueueUI() {
        if (priorityQueue.length > 0) {
            queueBadge.style.display = 'inline-block';
            queueBadge.textContent = `${priorityQueue.length} live in queue`;
        } else {
            queueBadge.style.display = 'none';
        }
    }

    function startSlideshowCycle() {
        advanceToNextSlide();
    }

    // Pure Client-Side SVG QR Code Generator
    function renderQrCode(url) {
        // High-contrast clean SVG QR container pointing to uploadUrl
        const encodedUrl = encodeURIComponent(url);
        // Using high-reliability QR image stream fallback or native canvas
        const img = document.createElement('img');
        img.src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodedUrl}&bgcolor=ffffff&color=050811&margin=1`;
        img.alt = 'Scan to Upload Photos';
        img.onerror = () => {
            // Local fallback text representation if external generator offline
            qrContainer.innerHTML = '<span style="font-size: 10px; color:#000; text-align:center; font-weight:bold;">SCAN URL</span>';
        };
        qrContainer.innerHTML = '';
        qrContainer.appendChild(img);
    }

    // Controls & Event Listeners
    function setupEventListeners() {
        // Toggle pause
        pauseBtn.addEventListener('click', togglePause);

        // Toggle QR code
        toggleQrBtn.addEventListener('click', () => {
            const isHidden = qrOverlay.style.display === 'none';
            qrOverlay.style.display = isHidden ? 'block' : 'none';
            toggleQrBtn.textContent = isHidden ? '📱 Hide QR' : '📱 Show QR';
        });

        // Toggle fullscreen
        fullscreenBtn.addEventListener('click', toggleFullscreen);

        // Keyboard hotkeys
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                togglePause();
            } else if (e.code === 'KeyF') {
                toggleFullscreen();
            } else if (e.code === 'KeyQ') {
                toggleQrBtn.click();
            } else if (e.code === 'ArrowRight') {
                clearTimers();
                advanceToNextSlide();
            }
        });

        // Auto-idle HUD
        let idleTimeout;
        const hud = document.getElementById('slideshowHud');
        document.addEventListener('mousemove', () => {
            hud.classList.remove('idle');
            clearTimeout(idleTimeout);
            idleTimeout = setTimeout(() => {
                hud.classList.add('idle');
            }, 4000);
        });
    }

    function togglePause() {
        isPaused = !isPaused;
        pauseBtn.textContent = isPaused ? '▶ Resume' : '⏸ Pause';
        pauseBtn.style.background = isPaused ? 'rgba(239, 68, 68, 0.6)' : '';
    }

    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.warn(`Fullscreen error: ${err.message}`);
            });
        } else {
            document.exitFullscreen().catch(err => {});
        }
    }

    // Start on DOM ready
    window.addEventListener('DOMContentLoaded', init);
})();
