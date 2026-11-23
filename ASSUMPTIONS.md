# ASSUMPTIONS.md

This document details every assumption, requirement gap filled, architectural tradeoff, and the rationale behind each design decision for the **Visitor Photo Slideshow** application.

---

## 1. Returning Visitor Identification

### The Problem / Gap in Requirements
The specification states: *"If the person is visiting again, the slideshow also plays their previous photos."* However, it does not specify how a returning visitor is recognized.

### Explored Approaches & Tradeoffs
1. **Name Alone (Rejected)**:
   - *Why rejected*: Names are not unique. Two distinct visitors named "Alex Smith" or "David Kim" would have their identities merged, causing one visitor's private memories to be shown under another person's submission.
2. **Biometric Face Recognition / Computer Vision (Rejected)**:
   - *Why rejected*: Raises severe privacy and legal compliance issues (GDPR Article 9, Illinois BIPA, Texas CUBI). Facial recognition also introduces latency, non-deterministic false positives/negatives, requires specialized heavy ML dependencies, and feels invasive for a casual event or office setting.
3. **Compound Key: Name + Secondary Identifier (Chosen)**:
   - *Why chosen*: We identify visitors using `(Name, Secondary Identifier)` where the secondary identifier can be an **Email Address, Phone Number, or Unique Tag/Handle**.
   - *Normalization*: Both fields are automatically trimmed of leading/trailing whitespace and normalized to lowercase (`name.strip()`, `secondary_identifier.strip().lower()`).
   - *Experience*: Easy and frictionless for the visitor. Visitors don't need to remember a complex password; entering their familiar phone number or email instantly links their current visit with past visits.

---

## 2. Privacy, Consent, and Public Display

### The Problem / Gap in Requirements
Photos of people are displayed publicly on a smart TV or large display. In public venues, offices, or events, visitors must have autonomy over whether their faces and personal moments are broadcast to everyone in the room.

### Design Decisions & Solutions
1. **Explicit Display Consent**:
   - The upload form features a clear, explicit consent toggle: *"Display on Public Smart TV Slideshow"*.
   - If checked (`consent_display = 1`): The photo is pushed to the TV priority queue and added to the public ambient slideshow pool.
   - If unchecked (`consent_display = 0`): The photo is safely uploaded and stored for the visitor's private event record/album, but is **strictly excluded** from the TV display feed, the live SSE event stream, and public endpoints.
2. **EXIF Metadata Stripping & Privacy Sanitization**:
   - Smartphone camera photos embed sensitive EXIF metadata, including **precise GPS location coordinates**, camera serial numbers, device model, and creation timestamps.
   - *Solution*: Our image processing pipeline decodes and strips all EXIF metadata before saving to disk.
   - *Orientation Correction*: Before stripping EXIF, the system inspects the EXIF `Orientation` tag and performs an automatic lossless transposition (`ImageOps.exif_transpose`). This guarantees photos taken in portrait mode on an iPhone or Android phone appear upright on the landscape TV screen without leaking GPS tags.
3. **Self-Service Photo Deletion via 6-Character PIN**:
   - Upon completing check-in, the visitor is issued a personal 6-character alphanumeric PIN (e.g. `A7D2E9`).
   - The `/gallery` portal provides a self-service deletion form: the visitor enters their Photo ID and their PIN to immediately remove the photo.
   - When deleted:
     - The record is flagged as `is_deleted = 1` (soft deletion prevents broken references).
     - A real-time `photo_deleted` event is broadcast across the Server-Sent Events stream. If the photo is currently on screen or queued in memory, connected smart TV screens immediately drop it and advance to the next slide.
4. **Configurable Retention Period**:
   - `PHOTO_RETENTION_HOURS` in configuration allows venue administrators to automatically expire or unlist old photos after a designated timeframe (e.g. 24 hours for daily events).

---

## 3. File Validation, Upload Size Limits, and Security

### The Problem / Gap in Requirements
Allowing public file uploads is an attack vector for denial of service (DoS), disk exhaustion, decompression bombs, and malicious file execution (e.g. uploading a PHP/Python script disguised as an image).

### Multi-Layer Security Architecture
1. **Strict Extension Whitelist**:
   - Only `.jpg`, `.jpeg`, `.png`, and `.webp` extensions are permitted.
2. **Magic Bytes Header Verification**:
   - File extensions can be trivially faked (e.g. renaming `malicious.exe` or `shell.sh` to `photo.jpg`).
   - The server inspects the first 12 bytes of the raw stream to verify cryptographic magic signatures:
     - JPEG: `\xFF\xD8\xFF`
     - PNG: `\x89PNG\r\n\x1a\n`
     - WebP: `RIFF` + `WEBP` tag at byte offset 8.
3. **Pillow Structural Integrity Check**:
   - `Image.open().verify()` ensures the file is a structurally valid, uncorrupted image and not a polyglot attack or truncated file.
4. **Decompression Bomb Protection**:
   - Attackers can upload small 10KB images that expand into gigabytes in memory when decompressed (decompression bomb).
   - We enforce `MAX_IMAGE_DIMENSION = 4096px`. Images larger than this threshold are safely downsampled using Lanczos filtering to preserve RAM.
5. **Path Traversal Prevention**:
   - Files are never saved using user-supplied filenames.
   - A cryptographically random UUIDv4 (`uuid.uuid4().hex`) is generated for every stored file (e.g. `4f8a9e21...jpg`). This completely prevents directory traversal attacks (`../../`).
6. **Request Size Constraints**:
   - Per-photo limit: Default 10MB (configurable via `MAX_UPLOAD_SIZE_MB`).
   - Maximum photos per batch: Default 5 photos (configurable via `MAX_FILES_PER_UPLOAD`).
   - HTTP payload size enforced at the web server and application layer via `MAX_CONTENT_LENGTH`.

---

## 4. Concurrency & Simultaneous Uploads

### The Problem / Gap in Requirements
What happens when 5 or 10 visitors upload photos at the exact same moment (e.g. during event registration or after a group photo)?

### Architecture & Solutions
1. **Database Layer (SQLite in WAL Mode)**:
   - Standard SQLite locks the entire database during writes.
   - We configure SQLite with **Write-Ahead Logging (WAL)**: `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, and `PRAGMA busy_timeout=5000;`.
   - In WAL mode, reads and writes occur concurrently without blocking each other. Multiple simultaneous uploads write their visitor and photo records without lock contention.
2. **In-Memory Priority Queue (`SlideshowManager`)**:
   - Managed with Python's thread-safe `threading.Lock` and `queue.Queue`.
   - When concurrent uploads complete simultaneously:
     - Every upload batch is appended to the `LivePriorityQueue`.
     - Smart TV screens receive the queued items sequentially in fair FIFO order.
     - On-screen queue indicator displays: `"3 live in queue"`.
3. **Server-Sent Events (SSE) Multi-Client Fan-Out**:
   - The server maintains a decoupled pub-sub list of active TV clients.
   - When an upload completes, an SSE notification is dispatched to all connected displays in parallel.
   - If a smart TV network drops or buffers, other connected displays continue without interruption.

---

## 5. Smart TV Playback Experience & Duration

### The Problem / Gap in Requirements
*"As soon as an upload completes, the photo plays in a slideshow for a specific duration on a smart TV or computer display. If the person is visiting again, the slideshow also plays their previous photos."*

### Playback Logic & UX Decisions
1. **Immediate Live Priority**:
   - Newly uploaded photos preempt the ambient slideshow loop and play immediately.
2. **Returning Visitor Showcase**:
   - If a returning visitor uploads new photos:
     1. Their **new** photo(s) play first for `SLIDESHOW_DISPLAY_DURATION` (default 8 seconds).
     2. Immediately following the new photos, their **previous** visits' approved photos are retrieved and played sequentially for the same duration.
     3. An on-screen banner highlights: *"✨ Welcome back, Alex Rivera! (Visit #2) &bull; Showing 2 new photos & 3 past memories"*.
3. **Ambient Fallback Loop**:
   - When the live queue is exhausted, the TV smoothly transitions to cycling through all approved historical visitor photos.
   - If no photos exist yet, an ambient Standby Screen displays a welcoming invitation and QR code.
4. **On-Screen QR Code**:
   - The TV display features a corner QR code pointing directly to the upload URL. Visitors in the room can point their smartphone camera at the TV and immediately open the upload portal without typing URLs.
5. **Flicker-Free Crossfading & Ken Burns**:
   - Uses dual HTML layers (`slideLayerA` and `slideLayerB`) with CSS opacity transitions and slow pan-and-zoom animations. Transitioning slides never shows a black screen or white flash.
