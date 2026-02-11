import threading
import logging
import pyperclip
from state import global_state
from llm_service import LLMService
import server

class InterviewController:
    def __init__(self, update_callback, clipboard_callback, status_callback):
        self.llm_service = LLMService()
        self.update_callback = update_callback        # To update response UI
        self.clipboard_callback = clipboard_callback  # To update clipboard UI
        self.status_callback = status_callback        # To update status bar
        
        self.last_clipboard_content = ""
        self.query_enabled = False
        self.server_running = False
        
        self.polling_rate_ms = 1000
        self.debounce_ms = 750
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self._debounce_timer = None

    def start_monitoring(self):
        """Starts the clipboard monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
            
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stops the clipboard monitoring thread."""
        self.stop_event.set()
        if self._debounce_timer:
            self._debounce_timer.cancel()

    def _monitor_loop(self):
        """Background loop to check clipboard."""
        while not self.stop_event.is_set():
            try:
                current_content = pyperclip.paste()
                if (current_content is not None and 
                    current_content != self.last_clipboard_content and 
                    len(current_content) > 1):
                    
                    self.last_clipboard_content = current_content
                    self.clipboard_callback(current_content)
                    logging.info("New clipboard content detected.")
                    
                    if self.query_enabled:
                        self.status_callback("Clipboard changed. Debouncing...")
                        self._schedule_query(current_content)
                        
            except Exception as e:
                logging.error(f"Error reading clipboard: {e}")
            
            self.stop_event.wait(self.polling_rate_ms / 1000.0)

    def _schedule_query(self, text):
        """Handles debouncing logic."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(self.debounce_ms / 1000.0, self._run_query, [text])
        self._debounce_timer.start()

    def _run_query(self, text, model="gpt-4o-mini"):
        """Executes the API query."""
        self.status_callback("Querying OpenAI API...")
        try:
            output = self.llm_service.query_api(text, model)
            global_state.update_response(output)
            self.update_callback(output)
            self.status_callback("API response received.")
        except Exception as e:
            logging.exception("Error in query thread")
            self.update_callback(f"Error: {e}")
            self.status_callback("API Error.")

    def toggle_solving_mode(self):
        self.query_enabled = not self.query_enabled
        return self.query_enabled

    def toggle_server(self, host="0.0.0.0", port=5000):
        if self.server_running:
            server.stop_server()
            self.server_running = False
            return False, None
        else:
            server.start_server(host, port)
            self.server_running = True
            from utils import get_local_ip
            return True, f"http://{get_local_ip()}:{port}/"
