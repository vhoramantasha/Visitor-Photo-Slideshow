# 📸 Visitor Photo Slideshow

An intelligent, real-time visitor check-in and interactive smart TV photo slideshow application built with Python (Flask), Server-Sent Events (SSE), Pillow, SQLite (WAL mode), and modern responsive web technologies.

Designed for events, offices, exhibitions, and venues, this application enables visitors to scan an on-screen QR code or visit an upload portal on their smartphone, check in with their name, and upload photos. As soon as an upload completes, the photo immediately appears on a smart TV display for a specific duration with cinematic transitions. When a returning visitor checks in, the application seamlessly recalls and plays their previous visits' photos alongside their new uploads.

---

## 🌟 Key Features

- **Instant TV Display Synchronization**: Uses Server-Sent Events (SSE) to push uploaded photos to connected Smart TV screens and monitors in real time (sub-second latency) without polling.
- **Returning Visitor Recognition**: Intelligently identifies returning visitors using compound identity resolution (`Name` + `Phone/Email`), avoiding naive name collision bugs while remaining frictionless.
- **Memory Vault (Past Photo Playback)**: When a returning visitor uploads new photos, the slideshow immediately plays their new photos first, followed by a personalized showcase of their past photos.
- **Privacy & Public Consent Engine**:
  - Explicit opt-in consent toggle for public TV display.
  - Automatic EXIF metadata stripping (permanently removes sensitive GPS coordinates, camera serial numbers, and personal device tags).
  - Lossless automatic orientation correction (`exif_transpose`) so mobile portrait selfies never render sideways.
  - Self-service photo withdrawal: visitors receive a personal 6-character PIN to remove any of their photos from the slideshow at any time.
- **Robust Security & File Validation**:
  - Whitelist validation for JPEG, PNG, and WebP.
  - Magic byte binary inspection to prevent extension spoofing (e.g. executable scripts disguised as `.jpg`).
  - Structural integrity verification via Pillow (`verify()`).
  - Decompression bomb defense and file size constraints (default 10MB per image, up to 5 photos per upload).
  - Cryptographically secure UUIDv4 filenames preventing directory traversal.
- **High Concurrency & Lock-Free Storage**: SQLite configured with **Write-Ahead Logging (WAL)** and an in-memory priority queue (`SlideshowManager`) to process multiple simultaneous visitor uploads cleanly.
- **Cinematic Smart TV Experience**:
  - 1080p and 4K optimized responsive layout.
  - Smooth dual-layer crossfading with subtle Ken Burns pan-and-zoom animations.
  - Circular countdown timer indicating remaining slide duration.
  - On-screen scan-to-upload QR code overlay.
  - Keyboard hotkeys (`F` for Fullscreen, `Space` for Pause/Resume, `Q` for Toggle QR).
  - Ambient community loop and standby screen when no live queue is waiting.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+ & Flask 3.1
- **Image Processing & Security**: Pillow (PIL 12.1)
- **Database**: SQLite 3 with Write-Ahead Logging (WAL mode)
- **Real-Time Communication**: Server-Sent Events (SSE) via native HTTP streaming
- **Frontend**: Vanilla ES6 JavaScript, HTML5 semantic layout, Modern CSS3 with custom properties
- **Testing**: Python native `unittest` framework (20 automated unit, security, and concurrency tests)

---

## 🚀 Setup & Run Instructions

### Prerequisites
- Python 3.10 or higher installed (`python --version`)
- Standard package installer (`pip` or `uv`)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd visitor
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
Copy the example environment template:
```bash
# On Windows:
copy .env.example .env

# On Linux / macOS:
cp .env.example .env
```
Key configuration settings in `.env`:
- `SLIDESHOW_DISPLAY_DURATION`: Duration in seconds per slide (default: `8`)
- `MAX_UPLOAD_SIZE_MB`: Max size in MB per photo (default: `10`)
- `MAX_FILES_PER_UPLOAD`: Maximum photos in a single upload (default: `5`)
- `PHOTO_RETENTION_HOURS`: Duration before photos are archived (default: `24`)

### 5. Start the Application Server
```bash
python app.py
```
Or using Flask CLI:
```bash
flask run --host=0.0.0.0 --port=5000
```

The server will initialize the SQLite database automatically and print:
```text
==================================================
  VISITOR PHOTO SLIDESHOW APPLICATION RUNNING
  Upload Kiosk (Visitors):  http://localhost:5000/
  TV Slideshow Display:     http://localhost:5000/display
  Privacy & Gallery:        http://localhost:5000/gallery
==================================================
```

---

## 🖥️ Live Demo & Usage Walkthrough

1. **Launch the TV Slideshow**:
   - Open `http://localhost:5000/display` on a smart TV browser or computer monitor.
   - Press `F` to enter full-screen mode.
   - A standby screen appears with an on-screen QR code and URL.
2. **Visitor Check-In & Photo Upload**:
   - On a smartphone or second browser tab, navigate to `http://localhost:5000/` (or scan the TV's QR code).
   - Enter your name: `Alex Rivera`.
   - Enter your phone number or email: `alex@example.com`.
   - Select one or more photos (or take a selfie).
   - Ensure the public display consent box is checked.
   - Click **"Upload & Play on TV Display"**.
3. **Instant TV Playback**:
   - The TV display instantly transitions from standby, showing the welcome banner: `"🌟 Welcome, Alex Rivera!"`.
   - The photo plays with Ken Burns animation while the countdown timer ticks down for 8 seconds.
   - The visitor's screen displays a personal **6-character PIN** (e.g. `B4C9F1`).
4. **Returning Visitor Experience**:
   - On the upload page, enter the same name `Alex Rivera` and same email `alex@example.com`.
   - Select a new photo and upload.
   - The TV display immediately transitions to the new photo with a golden badge: `"✨ WELCOME BACK, Alex Rivera!"`.
   - After the new photo finishes, the TV immediately transitions to Alex's previously uploaded photo from their first visit!
5. **Privacy Self-Service Deletion**:
   - Visit `http://localhost:5000/gallery`.
   - Enter the Photo ID and the 6-character PIN to immediately withdraw the photo. The photo is removed from the TV display in real time.

---

## 🧪 Automated Testing

Run the automated test suite covering unit tests, security validation, privacy consent enforcement, and high-concurrency multi-threaded uploads:

```bash
python run_tests.py
```

### Test Results
```text
======================================================================
  RUNNING VISITOR PHOTO SLIDESHOW TEST SUITE
======================================================================
test_concurrent_uploads_thread_safety ... ok
test_slideshow_queue_priority_ordering ... ok
test_exif_sanitization ... ok
test_reject_empty_file ... ok
test_reject_invalid_extension ... ok
test_reject_spoofed_file_magic_bytes ... ok
test_valid_jpeg_processing ... ok
test_valid_png_processing ... ok
test_case_and_whitespace_insensitivity ... ok
test_first_time_visitor_creation ... ok
test_returning_visitor_detection ... ok
test_same_name_different_identifier_creates_separate_visitors ... ok
test_consented_photo_included_in_public_slideshow ... ok
test_self_service_deletion_with_pin ... ok
test_unconsented_photo_excluded_from_public_slideshow ... ok
test_missing_name_returns_400 ... ok
test_missing_secondary_identifier_returns_400 ... ok
test_too_many_files_rejected ... ok
test_upload_returning_visitor_includes_past_photos ... ok
test_upload_success_first_visit ... ok
----------------------------------------------------------------------
Ran 20 tests in 0.964s

OK
  Tests run: 20
  Failures:  0
  Errors:    0
  RESULT: ALL TESTS PASSED SUCCESSFULLY! [OK]
======================================================================
```
For detailed manual test cases and scenarios, see [TESTING.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/TESTING.md).

---

## 📂 Repository Structure & Documentation Index

| File / Document | Purpose & Description |
| :--- | :--- |
| **[README.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/README.md)** | Project overview, tech stack, installation, quickstart, and live demo guide. |
| **[ASSUMPTIONS.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/ASSUMPTIONS.md)** | Every requirement gap filled (returning visitor identification, privacy/consent model, concurrency, validation). |
| **[AI_LOG.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/AI_LOG.md)** | 7 key prompts and interactions, including 3 critical cases where AI proposed flawed solutions and how they were caught and fixed. |
| **[ARCHITECTURE.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/ARCHITECTURE.md)** | Stack justification, system diagrams, database ER diagram, and sequence diagrams. |
| **[TESTING.md](file:///c:/Users/HP/OneDrive/Desktop/visitor/TESTING.md)** | Detailed test matrix, automated coverage, and step-by-step manual test procedures. |
| **[.env.example](file:///c:/Users/HP/OneDrive/Desktop/visitor/.env.example)** | Environment variable template with safe defaults. |
| **[run_tests.py](file:///c:/Users/HP/OneDrive/Desktop/visitor/run_tests.py)** | Single-command automated test runner. |
| **`app/`** | Application source code (models, database, services, routes, templates, static assets). |
| **`tests/`** | Hermetic test suite covering database, upload API, image validation, privacy, and concurrency. |

---

## 🔒 Security & Privacy Summary

1. **Zero Secret Leaks**: No API keys, passwords, or secrets are hardcoded. All configurations use `.env` placeholders.
2. **Decompression Bomb Protection**: Pillow safety limits prevent zip bomb attacks and memory exhaustion.
3. **Magic Byte Verification**: File binary headers are validated against recognized image signatures to prevent script upload vulnerabilities.
4. **EXIF GPS Stripping**: Sensitive location data and device metadata are automatically purged before storage.
5. **PIN-Protected Deletion**: Visitors retain complete control over their uploaded media with self-service PIN deletion.
