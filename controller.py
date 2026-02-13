import threading
import logging
import pyperclip
import keyboard
from state import global_state
from llm_service import LLMService
import server
import requests # Import requests for HTTP calls

class InterviewController:
    def __init__(self, update_callback, clipboard_callback, status_callback, monitoring_status_callback, response_loading_callback, qr_code_callback, visibility_callback=None, solving_mode_callback=None):
        self.llm_service = LLMService()
        self.update_callback = update_callback        # To update response UI
        self.clipboard_callback = clipboard_callback  # To update clipboard UI
        self.status_callback = status_callback        # To update status bar
        self.monitoring_status_callback = monitoring_status_callback # To update monitoring indicator
        self.response_loading_callback = response_loading_callback # To update response loading indicator
        self.qr_code_callback = qr_code_callback      # To update QR code display
        self.visibility_callback = visibility_callback # To toggle window visibility
        self.solving_mode_callback = solving_mode_callback # To sync UI button
        
        self.last_clipboard_content = ""
        self.query_enabled = False
        self.server_running = False
        self.server_ip = None  # Store server IP
        self.server_port = None # Store server port
        
        self.polling_rate_ms = 1000
        self.debounce_ms = 750
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self._debounce_timer = None
        
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        """Registers global hotkeys."""
        try:
            # Alt+S: Force solve from current clipboard
            keyboard.add_hotkey('alt+s', self.force_solve)
            # Alt+Q: Toggle solving mode
            keyboard.add_hotkey('alt+q', self.toggle_solving_mode_hotkey)
            # Alt+H: Toggle window visibility
            if self.visibility_callback:
                keyboard.add_hotkey('alt+h', self.visibility_callback)
            logging.info("Global hotkeys (Alt+S, Alt+Q, Alt+H) registered.")
        except Exception as e:
            logging.error(f"Failed to register hotkeys: {e}")

    def force_solve(self):
        """Manually triggers a solve from current clipboard."""
        current_content = pyperclip.paste()
        if current_content and len(current_content) > 1:
            logging.info("Manual solve triggered via hotkey.")
            self.status_callback("Manual solve triggered...")
            self.clipboard_callback(current_content)
            self._run_query(current_content, self.llm_service.model)

    def toggle_solving_mode_hotkey(self):
        """Hotkey wrapper for toggling solving mode."""
        new_state = self.toggle_solving_mode()
        self.status_callback(f"Solving Mode {'ACTIVE' if new_state else 'PAUSED'} (via hotkey)")

    def start_monitoring(self):
        """Starts the clipboard monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
            
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.monitoring_status_callback("Active", "green") # Initial status

    def stop_monitoring(self):
        """Stops the clipboard monitoring thread."""
        self.stop_event.set()
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self.monitoring_status_callback("Inactive", "red")

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
                        self.monitoring_status_callback("Clipboard detected, processing...", "orange") # Visual feedback
                        self._schedule_query(current_content)
                        
            except Exception as e:
                logging.error(f"Error reading clipboard: {e}")
            
            self.stop_event.wait(self.polling_rate_ms / 1000.0)

    def _schedule_query(self, text):
        """Handles debouncing logic."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(self.debounce_ms / 1000.0, self._run_query, [text, self.llm_service.model]) # Pass the current model
        self._debounce_timer.start()

    def _run_query(self, text, model):
        """Executes the API query with streaming."""
        self.status_callback("Querying OpenAI API (streaming)...")
        self.monitoring_status_callback("Querying AI...", "blue")
        self.response_loading_callback(True)
        
        full_response = ""
        try:
            for chunk in self.llm_service.query_api_stream(text, model):
                full_response += chunk
                # Update both UI and global state for phone display
                self.update_callback(full_response)
                global_state.update_response(full_response)
                
            self.status_callback("API response received.")
            if self.query_enabled:
                self.monitoring_status_callback("Active", "green")
            else:
                self.monitoring_status_callback("Paused", "gray")
        except Exception as e:
            logging.exception("Error in query thread")
            error_msg = f"Error: {e}"
            self.update_callback(error_msg)
            global_state.update_response(error_msg)
            self.status_callback("API Error.")
            self.monitoring_status_callback("Error, monitoring active", "red")
        finally:
            self.response_loading_callback(False)

    def toggle_solving_mode(self):
        self.query_enabled = not self.query_enabled
        if self.query_enabled:
            self.monitoring_status_callback("Active", "green")
        else:
            self.monitoring_status_callback("Paused", "gray")
        
        if self.solving_mode_callback:
            self.solving_mode_callback(self.query_enabled)
            
        return self.query_enabled

    def toggle_server(self, host="0.0.0.0", port=5000):
        if self.server_running:
            server.stop_server()
            self.server_running = False
            self.qr_code_callback(None) # Clear QR code when server stops
            self.server_ip = None
            self.server_port = None
            return False, None
        else:
            server.start_server(host, port)
            self.server_running = True
            from utils import get_local_ip
            self.server_ip = get_local_ip()
            self.server_port = port
            server_url = f"http://{self.server_ip}:{self.server_port}/"
            self.qr_code_callback(server_url) # Display QR code when server starts
            return True, server_url
    
    def send_test_message_to_server(self):
        """Sends a test message to the Flask server to verify connection."""
        if not self.server_running or not self.server_ip or not self.server_port:
            logging.warning("Attempted to send test message, but server is not running or IP/port are unknown.")
            return False
        
        try:
            test_url = f"http://{self.server_ip}:{self.server_port}/test_connection"
            response = requests.post(test_url, json={"message": "Test Connection from Desktop App"})
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            logging.info(f"Test message sent successfully to {test_url}. Response: {response.json()}")
            return True
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error while sending test message: {e}")
            return False
        except requests.exceptions.Timeout:
            logging.error("Timeout error while sending test message.")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending test message to Flask server: {e}")
            return False
