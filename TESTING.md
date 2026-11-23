# Testing Guide & Results

This document describes the testing strategy, test coverage, execution instructions, and manual test plan for the **Visitor Photo Slideshow** application.

---

## 1. Automated Test Suite

The automated test suite is built on Python's native `unittest` framework (no external test runner dependencies required), providing fast, hermetic, and deterministic test execution with zero side effects on production data.

### Running the Automated Tests

Execute the test runner from the root directory:

```bash
python run_tests.py
```

Or using Python's standard test discovery:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Coverage Summary

| Test Module | Coverage Scope | Tests | Result |
| :--- | :--- | :---: | :---: |
| `tests/test_models_and_db.py` | Database schema initialization, visitor creation, returning visitor detection, case/whitespace normalization, compound key uniqueness. | 4 | **PASSED** |
| `tests/test_image_validation.py` | Valid JPEG/PNG/WebP processing, file extension whitelist, spoofed magic bytes detection, empty files, EXIF orientation and metadata stripping. | 6 | **PASSED** |
| `tests/test_upload_api.py` | `POST /api/upload` endpoint, first-visit vs returning visit flows, past photos retrieval, missing required fields, upload file limit enforcement. | 5 | **PASSED** |
| `tests/test_privacy_and_consent.py` | Public consent flag enforcement, unconsented photo exclusion from slideshow, self-service deletion using 6-character PIN, invalid PIN rejection. | 3 | **PASSED** |
| `tests/test_concurrency_and_queue.py` | Multi-threaded concurrent uploads (6 simultaneous workers), SQLite WAL concurrency without locks, priority queue FIFO fairness. | 2 | **PASSED** |
| **Total** | **End-to-End System Validation** | **20** | **100% PASSED** |

---

## 2. Manual Test Plan

Use this manual test plan for live demo verification or browser smoke testing.

### Scenario A: First-Time Visitor Upload & Instant TV Playback
1. Open the TV Slideshow display in one browser tab: `http://localhost:5000/display`.
2. Notice the standby screen with the venue welcome message and scan-to-upload QR code.
3. Open the visitor upload kiosk in a second window or phone: `http://localhost:5000/`.
4. Enter Name: `Alex Rivera` and Identifier: `alex@example.com`.
5. Select or take a photo (`.jpg` or `.png`).
6. Ensure "Display on Public Smart TV Slideshow" is checked.
7. Click **"Upload & Play on TV Display"**.
8. **Expected Result**:
   - The upload form transitions to a success screen showing Alex's unique 6-character PIN (e.g. `A8B3C1`).
   - The TV display instantly transitions from standby, showing the welcome banner: `"🌟 Welcome, Alex Rivera! Showing new photo"`.
   - The countdown timer ticks down for 8 seconds with smooth Ken Burns pan-and-zoom animation.

### Scenario B: Returning Visitor Recognition & Past Photo Vault
1. Return to the upload page `http://localhost:5000/`.
2. Enter the same name `Alex Rivera` and identifier `alex@example.com`.
3. Select a second, different photo.
4. Click **"Upload & Play on TV Display"**.
5. **Expected Result**:
   - Upload response recognizes Alex: `"Welcome back, Alex Rivera! Your new photo and 1 past photo are playing on the slideshow display."`
   - The TV display instantly transitions to the new photo with a golden badge: `"✨ WELCOME BACK, Alex Rivera!"`.
   - After the new photo finishes its 8-second duration, the TV immediately transitions to Alex's first photo with the label: `"📸 MEMORY VAULT &bull; Past Memory from Alex Rivera (Visit #1)"`.

### Scenario C: Privacy Opt-Out (Private Storage Only)
1. Go to `http://localhost:5000/`.
2. Enter Name: `Private Guest` and Identifier: `guest@private.com`.
3. Select an image.
4. **Uncheck** the checkbox: *"Display on Public Smart TV Slideshow"*.
5. Submit the upload.
6. **Expected Result**:
   - Message states: `"Your photos were saved securely (not displayed on public screens as per your privacy preference)"`.
   - The TV slideshow does **not** interrupt and does **not** queue this photo.
   - Inspecting `http://localhost:5000/api/slideshow/all` confirms this photo is excluded from public display.

### Scenario D: Self-Service Photo Deletion via PIN
1. Note the Photo ID from `http://localhost:5000/gallery` (e.g. `ID: #1`).
2. Navigate to `http://localhost:5000/gallery`.
3. In the deletion form, enter Photo ID `1` and an incorrect PIN `000000`.
4. Submit. **Expected Result**: Rejection error: `"Deletion failed: Photo not found or invalid recovery PIN."`
5. Now enter the correct PIN provided at check-in (e.g. `A8B3C1`).
6. Submit. **Expected Result**:
   - Success message confirms deletion.
   - The card smoothly fades and removes from the gallery.
   - A `photo_deleted` event is broadcast over SSE; if that photo was active on the TV screen, the TV immediately advances to the next slide.

### Scenario E: Security & File Spoofing Protection
1. Create a text file or bash script named `fake_image.jpg` with arbitrary text.
2. Attempt to upload `fake_image.jpg` via `http://localhost:5000/`.
3. **Expected Result**:
   - The form immediately displays an error: `"File content does not match recognized image signatures (JPEG, PNG, WebP)"`.
   - No file is written to the server storage.
