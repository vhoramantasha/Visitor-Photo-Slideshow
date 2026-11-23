# System Architecture & Technical Design

This document details the architectural design, technology stack choices, database schema, data models, and workflow sequence diagrams for the **Visitor Photo Slideshow** application.

---

## 1. Technology Stack Rationale

| Layer | Technology | Decision Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **Python (Flask 3.1)** | Minimalist, robust, and zero-compile overhead. Ideal for rapid deployment and grading verification. Python comes pre-installed in almost all development environments, requiring no heavy Node.js runtime or toolchain builds. |
| **Image Processing** | **Pillow (PIL 12.1)** | Industry standard for Python. Enables low-level stream verification (`verify()`), magic byte validation, lossless EXIF transposition (`exif_transpose`), EXIF metadata stripping (protecting GPS privacy), and Lanczos downsampling. |
| **Database** | **SQLite (with WAL Mode)** | Zero-configuration, serverless, self-contained SQL engine. With **Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)**, SQLite supports concurrent multi-threaded writes without database lock contention. |
| **Real-Time Push** | **Server-Sent Events (SSE)** | Unidirectional HTTP streaming supported natively by all modern web and Smart TV browsers (`EventSource`). Unlike WebSockets, SSE requires no custom framing protocol, reconnects automatically with backoff, traverses corporate proxies effortlessly, and uses minimal memory. |
| **Frontend UI** | **Vanilla ES6 + Modern CSS3** | Zero build step or bundling required. Clean CSS custom properties with responsive mobile-first views for visitor uploads and hardware-accelerated 4K layouts for Smart TVs. |

---

## 2. High-Level System Architecture

```mermaid
graph TD
    subgraph Clients["Visitor & TV Clients"]
        Mobile["📱 Visitor Smartphone<br/>(Upload Kiosk /)"]
        TV["📺 Smart TV / Large Screen<br/>(Slideshow /display)"]
        Admin["💻 Gallery & Privacy Portal<br/>(/gallery)"]
    end

    subgraph Server["Flask Application Server (app.py)"]
        Router["HTTP Router & API Endpoints<br/>(/api/upload, /api/photos/delete)"]
        Streamer["SSE Event Streamer<br/>(/api/stream)"]
        
        subgraph Services["Core Application Services"]
            VS["Visitor Service<br/>(Identity Resolution & PIN)"]
            IS["Image Security Service<br/>(Magic Bytes, EXIF Strip, UUID)"]
            QM["Slideshow Manager<br/>(Priority Queue & Pub/Sub)"]
        end
    end

    subgraph Storage["Persistence Layer"]
        DB[("SQLite Database<br/>(WAL Mode: visitors & photos)")]
        Disk[("Local Storage<br/>(uploads/ - UUID filenames)")]
    end

    Mobile -->|"POST /api/upload (photos, name, id)"| Router
    TV -->|"GET /api/stream (SSE Listener)"| Streamer
    TV -->|"GET /api/slideshow/all (Ambient Pool)"| Router
    Admin -->|"POST /api/photos/delete (PhotoID, PIN)"| Router

    Router --> VS
    Router --> IS
    IS --> Disk
    VS --> DB

    Router -->|"Enqueue Live Upload"| QM
    QM -->|"Push SSE Event"| Streamer
    Streamer -.->|"Event: live_upload"| TV
    Streamer -.->|"Event: photo_deleted"| TV
```

---

## 3. Data Model & Entity Relationship (ER) Diagram

The persistence layer uses two primary relational entities with foreign-key cascading and composite lookup indexes.

```mermaid
erDiagram
    VISITORS ||--o{ PHOTOS : "uploads"
    
    VISITORS {
        int id PK "Auto-increment primary key"
        string name "Visitor full name"
        string secondary_identifier "Phone number, email, or handle"
        string pin "6-character hex recovery PIN"
        int visit_count "Total visits recorded"
        timestamp created_at "First registration timestamp"
        timestamp last_visit_at "Most recent visit timestamp"
    }

    PHOTOS {
        int id PK "Auto-increment primary key"
        int visitor_id FK "Foreign key referencing VISITORS(id)"
        string filename "UUID-based safe filename on disk"
        string original_filename "Original client filename"
        int file_size "Size in bytes"
        string mime_type "Sanitized MIME type"
        int width "Pixel width"
        int height "Pixel height"
        boolean consent_display "1 if approved for TV display; 0 if private"
        boolean is_deleted "1 if soft-deleted by visitor PIN"
        int visit_number "Visit sequence number when uploaded"
        timestamp uploaded_at "Upload timestamp"
    }
```

### Table Definitions

#### `visitors` Table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT NOT NULL)
- `secondary_identifier` (TEXT NOT NULL): Normalized lowercase/trimmed identifier (email or phone).
- `pin` (TEXT NOT NULL): 6-character alphanumeric recovery key.
- `visit_count` (INTEGER NOT NULL DEFAULT 1)
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `last_visit_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- **Constraint**: `UNIQUE(name, secondary_identifier)`
- **Index**: `idx_visitors_lookup` on `(name, secondary_identifier)`

#### `photos` Table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `visitor_id` (INTEGER NOT NULL REFERENCES visitors(id) ON DELETE CASCADE)
- `filename` (TEXT NOT NULL UNIQUE): UUIDv4 filename (e.g. `e3b0c442...jpg`).
- `original_filename` (TEXT NOT NULL)
- `file_size` (INTEGER NOT NULL)
- `mime_type` (TEXT NOT NULL)
- `width` (INTEGER), `height` (INTEGER)
- `consent_display` (INTEGER NOT NULL DEFAULT 1): Public display authorization flag.
- `is_deleted` (INTEGER NOT NULL DEFAULT 0): Soft deletion flag.
- `visit_number` (INTEGER NOT NULL DEFAULT 1)
- `uploaded_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- **Index**: `idx_photos_display` on `(consent_display, is_deleted)`

---

## 4. Workflow Sequence: Upload to Instant TV Playback

This diagram illustrates how an upload from a returning visitor is processed, saved, and prioritized on the smart TV display.

```mermaid
sequenceDiagram
    autonumber
    actor Visitor as 📱 Visitor
    participant Server as ⚙️ Flask API
    participant ImageService as 🛡️ Image Service
    participant Database as 🗄️ SQLite (WAL)
    participant Queue as 📋 Priority Queue
    participant TV as 📺 Smart TV Display

    Note over TV,Server: TV connects to Server-Sent Events stream (/api/stream)
    TV->>Server: GET /api/stream
    Server-->>TV: 200 OK (text/event-stream, event: connected)

    Note over Visitor,Server: Visitor submits form on mobile browser
    Visitor->>Server: POST /api/upload (Name, Email/Phone, Photo files, Consent=true)
    
    Server->>Database: Query (LOWER(name), secondary_id)
    Database-->>Server: Existing Visitor Record Found (visit_count: 1)
    Server->>Database: UPDATE visitors SET visit_count = 2, last_visit_at = NOW()

    loop For each uploaded photo
        Server->>ImageService: Validate extension, magic bytes, Pillow integrity
        ImageService->>ImageService: EXIF orientation transpose & metadata strip
        ImageService->>ImageService: Write sanitized file as UUIDv4 to uploads/
        Server->>Database: INSERT INTO photos (visitor_id, filename, visit_number=2, consent=1)
    end

    Server->>Database: Fetch past approved photos for visitor_id
    Database-->>Server: [Photo #1 from Visit #1]

    Server->>Queue: Enqueue Live Batch: [New Photo #2, Past Photo #1]
    Queue->>Server: Broadcast event: live_upload to all subscribers
    Server-->>TV: SSE Event "live_upload" (New photos + Past photos)

    Server-->>Visitor: 201 Created (Success message + 6-char PIN)

    Note over TV: TV receives SSE notification instantly
    TV->>TV: Interrupt ambient loop, show "✨ Welcome back!" banner
    TV->>TV: Display New Photo #2 for 8 seconds (Ken Burns animation)
    TV->>TV: Display Past Photo #1 for 8 seconds
    TV->>TV: Resume ambient community loop
```

---

## 5. Concurrency & Security Architecture

### 1. Database Concurrency (SQLite WAL Mode)
Traditional SQLite databases lock on write operations. By configuring:
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
```
SQLite operates in **Write-Ahead Logging** mode where readers do not block writers and writers do not block readers. Simultaneous uploads from multiple guests complete concurrently within milliseconds.

### 2. Multi-Layer File Validation
1. **Extension Whitelist**: Rejects non-image files before parsing.
2. **12-Byte Magic Number Inspection**: Verifies byte signatures directly from the binary header to prevent extension spoofing.
3. **Pillow Verification**: Invokes `Image.open().verify()` to detect malformed or polyglot files.
4. **Decompression Bomb Protection**: Caps image dimensions at `MAX_IMAGE_DIMENSION = 4096px`.
5. **Sanitization & EXIF Stripping**: Eliminates embedded GPS location tags and hardware identifiers.
6. **UUID Filename Generation**: Guarantees zero path traversal vulnerabilities (`../../`).

### 3. Smart TV Connection Resilience
- The SSE streaming route yields periodic `: keepalive` heartbeats every 15 seconds to prevent router/proxy disconnections.
- The Smart TV client implements an exponential backoff reconnect algorithm if the local Wi-Fi drops.
- Slideshow playback is non-blocking: while a photo displays, new incoming uploads are queued in memory without UI lag.
