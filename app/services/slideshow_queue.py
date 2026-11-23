import json
import time
import queue
import threading
from typing import List, Dict, Any, Optional
from app.config import Config

class SlideshowManager:
    """
    Thread-safe manager for real-time TV slideshow coordination and SSE broadcast.
    Handles:
    - Multi-subscriber SSE dispatch (fan-out to all connected TV screens)
    - Live Priority Queue: when a visitor uploads photos, they are queued first.
    - Returning visitor batching: new photos play first, followed by past photos.
    - Ambient loop state fallback when live queue is empty.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue] = []
        self._live_priority_queue: List[Dict[str, Any]] = []

    def subscribe(self) -> queue.Queue:
        """Register a new client (TV / browser display) stream listener."""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        """Remove a disconnected client queue."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Fan-out an event to all connected displays in SSE format."""
        payload = json.dumps({"type": event_type, "data": data, "timestamp": time.time()})
        sse_message = f"event: {event_type}\ndata: {payload}\n\n"

        with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(sse_message)
                except queue.Full:
                    # Client buffer full or stalled
                    dead_queues.append(q)
            for dead_q in dead_queues:
                if dead_q in self._subscribers:
                    self._subscribers.remove(dead_q)

    def enqueue_live_upload(
        self,
        visitor_name: str,
        is_returning: bool,
        visit_count: int,
        new_photos: List[Dict[str, Any]],
        past_photos: List[Dict[str, Any]] = None,
        duration: int = None,
    ):
        """
        Triggered when an upload completes:
        1. Formulates the showcase payload:
           - New photos play immediately.
           - If returning visitor, past photos play immediately after.
        2. Enqueues items to in-memory priority queue.
        3. Broadcasts instant 'live_upload' event to all active TV displays.
        """
        duration = duration or Config.SLIDESHOW_DISPLAY_DURATION
        past_photos = past_photos or []

        showcase_items = []

        # 1. New photos (highest priority)
        for idx, p in enumerate(new_photos):
            showcase_items.append({
                "photo_id": p.get("id"),
                "url": p.get("url"),
                "filename": p.get("filename"),
                "visitor_name": visitor_name,
                "is_returning": is_returning,
                "visit_count": visit_count,
                "is_new": True,
                "batch_index": idx + 1,
                "batch_total": len(new_photos),
                "duration": duration,
                "label": f"New Photo from {visitor_name}"
            })

        # 2. Returning visitor past photos
        for idx, p in enumerate(past_photos):
            showcase_items.append({
                "photo_id": p.get("id"),
                "url": p.get("url"),
                "filename": p.get("filename"),
                "visitor_name": visitor_name,
                "is_returning": True,
                "visit_count": visit_count,
                "is_new": False,
                "batch_index": idx + 1,
                "batch_total": len(past_photos),
                "duration": duration,
                "label": f"Past Memory from {visitor_name} (Visit #{p.get('visit_number', 1)})"
            })

        with self._lock:
            self._live_priority_queue.extend(showcase_items)

        # Broadcast live notification to all smart TV screens
        self.broadcast_event(
            "live_upload",
            {
                "visitor_name": visitor_name,
                "is_returning": is_returning,
                "visit_count": visit_count,
                "new_photos_count": len(new_photos),
                "past_photos_count": len(past_photos),
                "items": showcase_items,
                "duration": duration,
            },
        )

    def get_next_priority_item(self) -> Optional[Dict[str, Any]]:
        """Pop the next item from the live priority queue."""
        with self._lock:
            if self._live_priority_queue:
                return self._live_priority_queue.pop(0)
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """Return count of active subscribers and queued priority photos."""
        with self._lock:
            return {
                "active_displays": len(self._subscribers),
                "queued_priority_photos": len(self._live_priority_queue),
            }

# Global singleton instance
slideshow_manager = SlideshowManager()
