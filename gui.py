import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyperclip
import logging
from utils import get_local_ip
from state import global_state
import server
from llm_service import LLMService

class SimpleChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Interview AI Navigator")
        self.geometry("450x700") # Slightly larger
        self.attributes('-topmost', True)  # Always on top

        # --- Load Service ---
        self.llm_service = LLMService()
        if not self.llm_service.api_key:
             messagebox.showerror("Error", "OpenAI API key not found.\nPlease create a .env file with OPENAI_API_KEY=your_key")

        # --- State Variables ---
        self.last_clipboard_content = ""
        # We use global_state.latest_response for sharing with Flask
        self.query_enabled = False
        self.server_running = False
        self.server_thread = None
        self.polling_after_id = None # To cancel the polling loop on exit
        self.api_call_after_id = None # To manage debouncing API calls

        # --- Configuration ---
        self.polling_rate_ms = 1000  # Check clipboard every second
        self.debounce_ms = 750     # Wait 750ms after clipboard change before API call

        # --- OpenAI Model ---
        self.model_var = tk.StringVar(value="gpt-4o-mini") # Default model

        # --- Build UI ---
        self._create_widgets()

        # --- Start Processes ---
        self.update_status("Ready. Press 'Start Solving Mode' to begin.")
        self.start_clipboard_monitoring()

        # --- Handle Window Closing ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_widgets(self):
        """Creates and arranges the UI elements."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Model Selector
        model_frame = ttk.Frame(main_frame)
        ttk.Label(model_frame, text="AI Model:").pack(side=tk.LEFT, padx=(0, 5))
        model_selector = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=15,
                                      values=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]) # Added 3.5-turbo
        model_selector.pack(side=tk.LEFT)
        model_frame.pack(pady=(0, 10), anchor='w')

        # Clipboard Text Display
        clip_frame = ttk.LabelFrame(main_frame, text="Clipboard Content")
        # Use scrolledtext for automatic scrollbars
        self.clipboard_text = scrolledtext.ScrolledText(clip_frame, height=8, wrap=tk.WORD, state="disabled", relief=tk.FLAT, bg=self.cget('bg'))
        self.clipboard_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        clip_frame.pack(fill=tk.BOTH, pady=5)

        # ChatGPT Response Display
        resp_frame = ttk.LabelFrame(main_frame, text="Coding Hints / Response")
        self.response_text = scrolledtext.ScrolledText(resp_frame, height=15, wrap=tk.WORD, state="disabled", relief=tk.FLAT, bg=self.cget('bg'))
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        resp_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- Buttons Frame ---
        button_frame = ttk.Frame(main_frame)
        self.toggle_button = ttk.Button(button_frame, text="Start Solving Mode", command=self.toggle_query, width=20)
        self.toggle_button.pack(side=tk.LEFT, padx=5)

        self.server_button = ttk.Button(button_frame, text="Start Phone Server", command=self.toggle_server, width=20)
        self.server_button.pack(side=tk.LEFT, padx=5)
        button_frame.pack(pady=5)

        # --- Status Bar ---
        self.status_bar = ttk.Label(main_frame, text="Status: Initializing...", anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, pady=(10, 0), ipady=2) # Internal padding ipady

        # --- Server URL Label ---
        self.server_label = ttk.Label(main_frame, text="Server: Not running", anchor=tk.W)
        self.server_label.pack(fill=tk.X, pady=(5, 0))


    def update_status(self, message):
        """Updates the status bar text."""
        self.status_bar.config(text=f"Status: {message}")
        logging.info(f"Status: {message}") # Log status updates

    def start_clipboard_monitoring(self):
        """Initiates the clipboard checking loop."""
        # Clear any previous loop id
        if self.polling_after_id:
            self.after_cancel(self.polling_after_id)
            self.polling_after_id = None

        self.check_clipboard() # Start the first check

    def check_clipboard(self):
        """Checks the clipboard for changes and schedules the next check."""
        try:
            current_content = pyperclip.paste()
        except Exception as e: # Catch potential pyperclip errors
            logging.error(f"Error reading clipboard: {e}")
            current_content = None # Indicate error or inability to read

        # Process if content is readable and has changed significantly
        if current_content is not None and current_content != self.last_clipboard_content and len(current_content) > 1 : # Ignore empty/trivial changes
            self.last_clipboard_content = current_content
            self.update_clipboard_display(current_content)
            logging.info("New clipboard content detected.")
            self.update_status("Clipboard changed. Debouncing...")

            if self.query_enabled:
                # Cancel previous scheduled API call if it exists (debouncing)
                if self.api_call_after_id:
                    self.after_cancel(self.api_call_after_id)
                    logging.debug("Cancelled previous API call debounce timer.")

                # Schedule the API call after debounce period
                self.api_call_after_id = self.after(self.debounce_ms, self.schedule_api_query, current_content)
                logging.debug(f"Scheduled API query in {self.debounce_ms}ms.")

        # Schedule the next check
        self.polling_after_id = self.after(self.polling_rate_ms, self.check_clipboard)

    def schedule_api_query(self, text_to_query):
        """Called after debounce; starts the API query in a separate thread."""
        self.api_call_after_id = None # Clear the timer ID
        self.update_status("Querying OpenAI API...")
        logging.info("Debounce finished, starting API query thread.")
        # Start the actual API call in a background thread to avoid blocking the GUI
        thread = threading.Thread(target=self.query_api_thread, args=(text_to_query,), daemon=True)
        thread.start()

    def update_text_widget(self, text_widget, content):
        """Safely updates a Tkinter Text widget from any thread."""
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, content)
        text_widget.config(state="disabled")
        text_widget.see(tk.END) # Scroll to the end

    def update_clipboard_display(self, text):
        """Updates the clipboard display area on the main thread."""
        self.after(0, self.update_text_widget, self.clipboard_text, text)

    def update_response_display(self, text):
        """Updates the response display area and the shared state on the main thread."""
        global_state.update_response(text)  # Update shared state for Flask
        self.after(0, self.update_text_widget, self.response_text, text)
        self.after(0, self.update_status, "API response received.") # Update status bar via main thread


    def query_api_thread(self, prompt):
        """Runs the OpenAI API call in a separate thread."""
        model = self.model_var.get()
        logging.info(f"Sending query to model: {model}")
        
        try:
            output = self.llm_service.query_api(prompt, model)
            logging.info("API response successfully received.")
            # Schedule the GUI update on the main thread
            self.update_response_display(output)

        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logging.exception("An unexpected error occurred during API call") # Log full traceback
            self.update_response_display(f"Error querying API: {error_msg}")


    def toggle_query(self):
        """Toggles the solving mode on/off."""
        self.query_enabled = not self.query_enabled
        if self.query_enabled:
            self.toggle_button.config(text="Pause Solving Mode")
            self.update_status("Solving Mode ACTIVE. Monitoring clipboard...")
        else:
            self.toggle_button.config(text="Start Agent Mode")
        print(f"Querying {'enabled' if self.query_enabled else 'paused'}")

    def toggle_server(self):
        """Starts or stops the Flask server in a separate thread."""
        if self.server_running:
            # Stopping the server - Note: This won't cleanly stop app.run()
            # We rely on the thread being a daemon.
            self.server_running = False
            self.server_thread = None # Allow garbage collection
            self.server_label.config(text="Server: Not running")
            self.server_button.config(text="Start Phone Server")
            self.update_status("Flask server stopped (thread terminated).")
            logging.info("Flask server stopped (daemon thread will exit).")
        else:
            try:
                ip_address = get_local_ip()
                server_url = f"http://{ip_address}:5000/response"
                self.server_label.config(text=f"Server: Running at {server_url}")
                self.server_button.config(text="Stop Server")

                # Start Flask in a daemon thread via server module
                self.server_running = True
                self.server_thread = server.start_server_thread()
                
                self.update_status(f"Flask server started at {server_url}")
                logging.info(f"Flask server thread started at {server_url}")

            except Exception as e:
                logging.exception("Failed to start Flask server")
                self.server_label.config(text="Server: Error starting")
                self.server_button.config(text="Start Phone Server") # Reset button
                self.update_status(f"Error starting server: {e}")
                self.server_running = False # Ensure state is correct


    def on_closing(self):
        """Handles the window close event."""
        logging.info("Application closing...")
        self.update_status("Exiting...")
        # Stop clipboard polling loop
        if self.polling_after_id:
            self.after_cancel(self.polling_after_id)
            self.polling_after_id = None
            logging.debug("Clipboard polling stopped.")

        # Cancel any pending API call debounce
        if self.api_call_after_id:
            self.after_cancel(self.api_call_after_id)
            self.api_call_after_id = None
            logging.debug("Cancelled pending API call.")

        # No clean way to stop flask dev server thread here, relies on daemon=True
        if self.server_running:
             logging.info("Flask server thread is a daemon and will be terminated.")

        self.destroy() # Close the Tkinter window
