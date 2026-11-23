// Visitor Check-in & Photo Upload Portal
document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const photoInput = document.getElementById('photoInput');
    const dropZone = document.getElementById('dropZone');
    const previewGrid = document.getElementById('previewGrid');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');
    const statusMessage = document.getElementById('statusMessage');
    const successCard = document.getElementById('successCard');
    const successHeading = document.getElementById('successHeading');
    const successDetails = document.getElementById('successDetails');
    const displayPin = document.getElementById('displayPin');
    const resetBtn = document.getElementById('resetBtn');

    let selectedFiles = [];
    const MAX_FILES = 5;
    const MAX_SIZE_MB = 10;
    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        handleFiles(files);
    });

    photoInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleFiles(files);
    });

    function showStatus(text, type = 'error') {
        statusMessage.textContent = text;
        statusMessage.className = `status-banner ${type}`;
        statusMessage.style.display = 'block';
    }

    function clearStatus() {
        statusMessage.textContent = '';
        statusMessage.style.display = 'none';
    }

    function handleFiles(files) {
        clearStatus();
        let errorMsg = null;

        files.forEach(file => {
            if (selectedFiles.length >= MAX_FILES) {
                errorMsg = `Maximum ${MAX_FILES} photos allowed.`;
                return;
            }
            if (!ALLOWED_TYPES.includes(file.type)) {
                errorMsg = `File "${file.name}" is not a supported format (JPEG, PNG, WebP only).`;
                return;
            }
            if (file.size > MAX_SIZE_MB * 1024 * 1024) {
                errorMsg = `File "${file.name}" exceeds the ${MAX_SIZE_MB}MB size limit.`;
                return;
            }
            // Check for duplicate names
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });

        if (errorMsg) {
            showStatus(errorMsg, 'error');
        }

        renderPreviews();
    }

    function renderPreviews() {
        previewGrid.innerHTML = '';
        if (selectedFiles.length === 0) {
            previewGrid.style.display = 'none';
            return;
        }

        previewGrid.style.display = 'grid';
        selectedFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'preview-item';

            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.alt = file.name;

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'remove-btn';
            removeBtn.innerHTML = '&times;';
            removeBtn.title = 'Remove photo';
            removeBtn.addEventListener('click', () => {
                selectedFiles.splice(index, 1);
                renderPreviews();
            });

            item.appendChild(img);
            item.appendChild(removeBtn);
            previewGrid.appendChild(item);
        });
    }

    // Form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearStatus();

        const name = document.getElementById('name').value.trim();
        const secondaryId = document.getElementById('secondary_identifier').value.trim();
        const consent = document.getElementById('consent').checked;

        if (!name) {
            showStatus('Please enter your name.', 'error');
            return;
        }
        if (!secondaryId) {
            showStatus('Please provide an email or phone number to recognize your visits.', 'error');
            return;
        }
        if (selectedFiles.length === 0) {
            showStatus('Please select at least one photo to upload.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('name', name);
        formData.append('secondary_identifier', secondaryId);
        formData.append('consent', consent ? 'true' : 'false');

        selectedFiles.forEach(file => {
            formData.append('photos', file);
        });

        // Set loading state
        submitBtn.disabled = true;
        btnText.textContent = 'Uploading & Validating...';

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Upload failed. Please try again.');
            }

            // Success state
            uploadForm.style.display = 'none';
            successCard.style.display = 'block';

            if (result.is_returning) {
                successHeading.textContent = `Welcome Back, ${result.visitor.name}! ✨`;
                successDetails.textContent = `We recognized your previous visit! Your ${result.new_photos.length} new photo(s) and ${result.past_photos.length} past photo(s) are now playing on the TV slideshow display.`;
            } else {
                successHeading.textContent = `Welcome, ${result.visitor.name}! 🌟`;
                successDetails.textContent = result.consent_display
                    ? `Your photos are playing right now on the smart TV display!`
                    : `Your photos have been saved securely to your private album (not shown on TV screens).`;
            }

            displayPin.textContent = result.pin || '------';

        } catch (err) {
            showStatus(err.message, 'error');
            submitBtn.disabled = false;
            btnText.textContent = 'Upload & Play on TV Display';
        }
    });

    // Reset form
    resetBtn.addEventListener('click', () => {
        selectedFiles = [];
        photoInput.value = '';
        renderPreviews();
        clearStatus();
        uploadForm.reset();
        document.getElementById('consent').checked = true;
        submitBtn.disabled = false;
        btnText.textContent = 'Upload & Play on TV Display';
        successCard.style.display = 'none';
        uploadForm.style.display = 'block';
    });
});
