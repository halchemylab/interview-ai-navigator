class AppState:
    """Simple class to hold shared state between GUI and Server."""
    def __init__(self):
        self.latest_response = "No response yet."

# Global instance to be shared
global_state = AppState()
