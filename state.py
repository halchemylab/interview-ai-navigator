import threading

class AppState:
    """Simple class to hold shared state between GUI and Server."""
    def __init__(self):
        self._latest_response = "No response yet."
        self._condition = threading.Condition()

    @property
    def latest_response(self):
        with self._condition:
            return self._latest_response

    def update_response(self, new_response):
        """Updates the response and notifies waiting threads."""
        with self._condition:
            self._latest_response = new_response
            self._condition.notify_all()
    
    def wait_for_update(self, timeout=None):
        """Blocks until a new response is available."""
        with self._condition:
            return self._condition.wait(timeout)

# Global instance to be shared
global_state = AppState()
