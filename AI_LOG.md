# AI Collaboration Log (AI_LOG.md)

This log records the key prompts, architectural interactions, critical evaluations, and collaborative debugging sessions between the developer and AI during the design and implementation of the **Visitor Photo Slideshow** application.

---

## Interaction 1: Architecture & Real-Time Sync Strategy

### Developer Prompt
> "We need to build a visitor photo slideshow where photos uploaded from visitor smartphones instantly play on a smart TV display. Evaluate the best architecture that handles real-time push to the TV display without requiring complex server infrastructure or heavy external daemons."

### AI Initial Proposal
The AI suggested using a full Node.js / React stack with Socket.io and Redis for pub-sub messaging.

### Critical Evaluation & Decision
- **Developer Review**: Adding Node.js, React, Webpack/Vite build steps, and an external Redis daemon creates immense deployment friction, potential NPM build failures on different machines, and unnecessary resource overhead.
- **Human Direction**: "We want a lightweight, zero-compilation, highly portable architecture. Let's use Python (Flask) with Server-Sent Events (SSE) and native modern JavaScript. SSE works natively in all TV browsers without third-party client libraries, auto-reconnects, and requires no external Redis daemon."
- **Outcome**: Adopted Python + Flask + SSE + Vanilla ES6/CSS3. Reduced dependencies to just Flask, Pillow, Werkzeug, and Python's built-in libraries.

---

## Interaction 2: Returning Visitor Identification (Case 1: AI was Wrong)

### Developer Prompt
> "Implement the visitor check-in logic to satisfy the requirement: 'If the person is visiting again, the slideshow also plays their previous photos.' How should we structure the visitor model and lookup query?"

### AI Mistake / Proposed Code
The AI proposed a simple database query matching visitors purely by `name`:
```python
# AI'S FLAWED CODE
cur.execute("SELECT id, visit_count FROM visitors WHERE name = ?", (name,))
row = cur.fetchone()
if row:
    # Mark as returning visitor
    cur.execute("UPDATE visitors SET visit_count = visit_count + 1 WHERE id = ?", (row['id'],))
```

### How the Mistake Was Caught
During code review of the proposed database schema, I noticed a severe **name collision bug**:
1. Common names (e.g. "Alex Smith", "David Kim", "Maria Garcia") are not unique.
2. If Visitor A named "Alex Smith" checks in on Monday, and an entirely different Visitor B named "Alex Smith" checks in on Tuesday, the AI's logic would treat Visitor B as Visitor A, incrementing their visit count and **broadcasting Visitor A's private past photos alongside Visitor B's photos**.
3. This creates a critical privacy violation and data integrity breakdown.

### How It Was Fixed
I instructed the AI to implement a **compound identity key**:
```sql
CREATE TABLE visitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    secondary_identifier TEXT NOT NULL,  -- Phone number or email
    pin TEXT NOT NULL,
    visit_count INTEGER NOT NULL DEFAULT 1,
    UNIQUE(name, secondary_identifier)
);
```
With string normalization:
```python
clean_name = name.strip()
clean_id = secondary_identifier.strip().lower()
```
Now, two visitors named "Alex Smith" with different phone numbers or emails remain completely separate.

---

## Interaction 3: EXIF Privacy & Orientation Leak

### Developer Prompt
> "When visitors upload photos from mobile devices, how should the server process and store them to guarantee privacy and correct orientation?"

### AI Initial Proposal
The AI suggested saving the raw uploaded file directly with `werkzeug.utils.secure_filename(file.filename)`.

### Critical Evaluation & Human Guidance
- **Developer Review**: 
  1. Phone cameras (iOS/Android) embed sensitive EXIF tags: **exact GPS coordinates (latitude/longitude)**, device serials, and timestamps. Publicly displaying images with GPS tags exposes visitor locations.
  2. Mobile cameras save photos with an EXIF `Orientation` tag (1 to 8). If an image is stripped of EXIF or rendered in a browser without orientation handling, portrait photos render sideways (rotated 90° or 180°) on the TV screen!
- **Human Direction**: "We must transpose the image according to its EXIF orientation tag first, then strip all EXIF metadata before saving to disk. Additionally, we must generate a random UUIDv4 filename to eliminate directory traversal risks."
- **Outcome**: Implemented `ImageOps.exif_transpose(img)` followed by a clean save that removes all metadata tags, protecting visitor privacy while keeping orientations upright.

---

## Interaction 4: Server-Sent Events Generator Thread Starvation (Case 2: AI was Wrong)

### Developer Prompt
> "Write the Flask streaming endpoint `/api/stream` using Server-Sent Events so TV screens receive live updates."

### AI Mistake / Proposed Code
The AI provided this generator implementation:
```python
# AI'S FLAWED CODE
@stream_bp.route("/stream")
def sse_stream():
    def event_stream():
        q = slideshow_manager.subscribe()
        while True:
            # Flaw: Blocks indefinitely on an empty queue
            msg = q.get()
            yield msg
    return Response(event_stream(), mimetype="text/event-stream")
```

### How the Mistake Was Caught
During testing of client reconnections and server shutdowns, two severe issues appeared:
1. **Thread Starvation & Dead Connections**: `q.get()` without a timeout blocks the Flask request worker thread indefinitely if no uploads occur. When a smart TV browser tab closes or experiences a network glitch, the generator never unblocks, leaking threads and consumer queues in memory.
2. **Proxy Timeout Drops**: Corporate firewalls, reverse proxies (Nginx), and smart TV browser runtimes close HTTP connections that remain silent for more than 30–60 seconds.

### How It Was Fixed
I directed the AI to refactor the generator with:
1. A 15-second timeout on `q.get(timeout=15.0)`.
2. Periodic `: keepalive\n\n` comments on timeout to prevent network disconnects.
3. Proper `GeneratorExit` exception handling with guaranteed cleanup in a `finally` block:
```python
def event_stream():
    client_queue = slideshow_manager.subscribe()
    try:
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
        while True:
            try:
                msg = client_queue.get(timeout=15.0)
                yield msg
            except queue.Empty:
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        slideshow_manager.unsubscribe(client_queue)
```

---

## Interaction 5: Upload File Security & Magic Bytes Verification

### Developer Prompt
> "Visitors will be uploading files through a public form. How should we ensure malicious users cannot upload executable scripts or exploit file parsing?"

### AI Initial Proposal
The AI suggested verifying the MIME type from `file.content_type` and checking if `filename.endswith(('.jpg', '.png'))`.

### Critical Evaluation & Human Guidance
- **Developer Review**: Both `file.content_type` and the file extension can be freely manipulated by an attacker (e.g. an attacker can send a PHP script named `exploit.jpg` with `Content-Type: image/jpeg`).
- **Human Direction**: "We need true defence-in-depth:
  1. Extension whitelist.
  2. Raw 12-byte magic byte signature verification (JPEG `\xFF\xD8\xFF`, PNG `\x89PNG`, WebP `RIFF...WEBP`).
  3. Pillow `Image.open().verify()` to catch corrupted files and polyglots.
  4. Decompression bomb protection with `MAX_IMAGE_DIMENSION`."
- **Outcome**: Implemented the multi-layer security pipeline in `ImageService.process_and_save_image()`.

---

## Interaction 6: Configuration Overrides in API Routes (Case 3: AI was Wrong)

### Developer Prompt
> "Connect the API upload validation to the application's configuration settings."

### AI Mistake / Proposed Code
The AI implemented the limit check by importing the static class attribute:
```python
# AI'S FLAWED CODE
from app.config import Config
...
if len(files) > Config.MAX_FILES_PER_UPLOAD:
    return jsonify({"error": "Too many files"}), 400
```

### How the Mistake Was Caught
When executing the automated test suite (`python run_tests.py`), `test_too_many_files_rejected` failed with:
`AssertionError: 201 != 400`.
In the test setup, `MAX_FILES_PER_UPLOAD = 3` had been passed to the app test config. But because the AI hardcoded `Config.MAX_FILES_PER_UPLOAD` (which defaulted to 5) instead of querying the Flask application runtime config `current_app.config`, the test environment's configuration was ignored.

### How It Was Fixed
I updated `app/routes/api.py` to always reference the active application configuration:
```python
max_files = current_app.config.get("MAX_FILES_PER_UPLOAD", Config.MAX_FILES_PER_UPLOAD)
if len(files) > max_files:
    return jsonify({"error": f"Too many files selected. Maximum is {max_files} photos per upload."}), 400
```
Rerunning `python run_tests.py` immediately resulted in a 100% pass rate across all 20 tests.

---

## Interaction 7: Smart TV HUD, QR Code Pairing, and Ambient Queue

### Developer Prompt
> "Design the Smart TV display interface. It needs to look cinematic on 1080p and 4K screens, smoothly cross-fade photos without flicker, and allow visitors in the room to easily upload without typing long URLs."

### AI Collaborative Implementation
- Designed dual-layer HTML crossfade (`#slideLayerA` and `#slideLayerB`) with CSS Ken Burns animation.
- Implemented a circular SVG progress countdown ring synced with `SLIDESHOW_DISPLAY_DURATION`.
- Added a corner QR code pointing dynamically to `uploadUrl` (so guests at the venue can scan the TV with their smartphone camera to upload immediately).
- Built an idle-sensing HUD (hides controls after 4 seconds of inactivity).
- Added keyboard shortcuts (`F` for Fullscreen, `Space` for Pause/Resume, `Q` for Toggle QR).
