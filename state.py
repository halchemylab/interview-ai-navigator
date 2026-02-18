import threading

class AppState:
    """Simple class to hold shared state between GUI and Server."""
    def __init__(self):
        self._latest_response = "No response yet."
        self._history = []  # List of strings for previous full responses
        self._active_ocr_region = None # (x, y, w, h) tuple for active OCR monitoring
        self._last_ocr_content = ""    # Last text extracted from the active OCR region
        self._condition = threading.Condition()

    @property
    def latest_response(self):
        with self._condition:
            return self._latest_response

    @property
    def history(self):
        with self._condition:
            return list(self._history)

    @property
    def active_ocr_region(self):
        with self._condition:
            return self._active_ocr_region

    @active_ocr_region.setter
    def active_ocr_region(self, region):
        with self._condition:
            self._active_ocr_region = region
            self._condition.notify_all()

    @property
    def last_ocr_content(self):
        with self._condition:
            return self._last_ocr_content

    @last_ocr_content.setter
    def last_ocr_content(self, content):
        with self._condition:
            self._last_ocr_content = content
            self._condition.notify_all()

    def update_response(self, new_response):
        """Updates the current response and notifies waiting threads."""
        with self._condition:
            self._latest_response = new_response
            self._condition.notify_all()
    
    def finalize_response(self):
        """Moves the current response into the history list."""
        with self._condition:
            if self._latest_response and self._latest_response != "No response yet.":
                # Avoid duplicates if finalize is called multiple times for same content
                if not self._history or self._history[-1] != self._latest_response:
                    self._history.append(self._latest_response)
            self._condition.notify_all()

    def wait_for_update(self, timeout=None):
        """Blocks until a new response is available."""
        with self._condition:
            return self._condition.wait(timeout)

# Global instance to be shared
global_state = AppState()
