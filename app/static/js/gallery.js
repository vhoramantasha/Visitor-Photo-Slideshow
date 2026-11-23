// Visitor Archive & Privacy Self-Service Deletion Controller
document.addEventListener('DOMContentLoaded', () => {
    const deleteForm = document.getElementById('deleteForm');
    const deletePhotoId = document.getElementById('deletePhotoId');
    const deletePin = document.getElementById('deletePin');
    const deleteFeedback = document.getElementById('deleteFeedback');

    deleteForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const photoId = deletePhotoId.value.trim();
        const pin = deletePin.value.trim().toUpperCase();

        if (!photoId || !pin) {
            showFeedback('Please provide both Photo ID and your 6-character PIN.', 'error');
            return;
        }

        try {
            const res = await fetch('/api/photos/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ photo_id: photoId, pin: pin })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Failed to delete photo.');
            }

            showFeedback('Success: Photo has been removed from the slideshow and gallery!', 'success');
            
            // Remove the card from the UI
            const card = document.getElementById(`photo-card-${photoId}`);
            if (card) {
                card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.8)';
                setTimeout(() => card.remove(), 400);
            }

            deleteForm.reset();
        } catch (err) {
            showFeedback(err.message, 'error');
        }
    });

    function showFeedback(text, type) {
        deleteFeedback.textContent = text;
        deleteFeedback.className = `delete-feedback status-banner ${type}`;
        deleteFeedback.style.display = 'block';
    }
});
