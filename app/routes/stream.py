import json
import queue
import time
from flask import Blueprint, Response, stream_with_context, current_app
from app.services.slideshow_queue import slideshow_manager

stream_bp = Blueprint("stream", __name__)

@stream_bp.route("/stream")
def sse_stream():
    """
    Server-Sent Events (SSE) real-time stream endpoint for TV displays.
    Pushes:
    - 'connected' handshake event
    - 'live_upload' event when visitors submit photos
    - 'photo_deleted' event when photos are withdrawn
    - Periodic ': keepalive' comments to maintain persistent connection across proxies/routers
    """
    def event_stream():
        client_queue = slideshow_manager.subscribe()
        try:
            # Send initial connected handshake
            init_data = json.dumps({"status": "connected", "time": time.time()})
            yield f"event: connected\ndata: {init_data}\n\n"

            while True:
                try:
                    # Non-blocking wait with 15s timeout
                    msg = client_queue.get(timeout=15.0)
                    yield msg
                except queue.Empty:
                    # Keep connection alive across firewalls/proxies
                    yield ": keepalive\n\n"
        except GeneratorExit:
            # Client closed tab or disconnected
            pass
        finally:
            slideshow_manager.unsubscribe(client_queue)

    response = Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream"
    )
    # Crucial headers for real-time SSE streaming without buffering
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response
