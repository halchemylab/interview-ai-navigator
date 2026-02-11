import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyperclip
import logging
from dotenv import load_dotenv, set_key
from utils import get_local_ip
import server
from llm_service import LLMService
from controller import InterviewController # Import the new controller
import qrcode
from PIL import Image, ImageTk # Import Pillow modules

class SimpleChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Interview AI Navigator")
        self.geometry("450x700") # Slightly larger
        self.attributes('-topmost', True)  # Always on top

        # --- Initialize Controller ---
        self.controller = InterviewController(
            update_callback=lambda text: self.after(0, self.update_response_display, text),
            clipboard_callback=lambda text: self.after(0, self.update_clipboard_display, text),
            status_callback=lambda text: self.after(0, self.update_status, text),
            monitoring_status_callback=lambda status, color: self.after(0, self.update_monitoring_indicator, status, color),
            response_loading_callback=lambda is_loading: self.after(0, self.set_response_loading_state, is_loading),
            qr_code_callback=lambda url: self.after(0, self.update_qr_code, url)
        )
        
        if not self.controller.llm_service.api_key:
             messagebox.showerror("Error", "OpenAI API key not found.\nPlease create a .env file with OPENAI_API_KEY=your_key or configure it in Settings.")

        # --- OpenAI Model ---
        self.model_var = tk.StringVar(value="gpt-4o-mini") # Default model

        # --- Build UI ---
        self._create_widgets()

        # --- Start Processes ---
        self.update_status("Ready. Press 'Start Solving Mode' to begin.")
        # self.controller.start_monitoring() # Removed from here, it's called in interview-solver.py
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
        model_selector.bind("<<ComboboxSelected>>", self.on_model_selected) # Bind event
        model_frame.pack(pady=(0, 10), anchor='w')

        # Monitoring Indicator
        self.monitoring_indicator = ttk.Label(main_frame, text="Monitoring: Inactive", anchor=tk.W, font=("Segoe UI", 9, "italic"))
        self.monitoring_indicator.pack(fill=tk.X, pady=(0, 5))

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

        self.settings_button = ttk.Button(button_frame, text="Settings", command=self.open_settings, width=15)
        self.settings_button.pack(side=tk.LEFT, padx=5)
        button_frame.pack(pady=5)

        # --- Status Bar ---
        self.status_bar = ttk.Label(main_frame, text="Status: Initializing...", anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, pady=(10, 0), ipady=2) # Internal padding ipady

        # --- Server URL Label ---
        self.server_label = ttk.Label(main_frame, text="Server: Not running", anchor=tk.W)
        self.server_label.pack(fill=tk.X, pady=(5, 0))

        # QR Code Display
        self.qr_code_label = ttk.Label(main_frame)
        self.qr_code_label.pack(pady=(5,0))


    def update_qr_code(self, url):
        """Generates and displays a QR code for the given URL, or clears it if url is None."""
        if url:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                img = img.resize((150, 150), Image.Resampling.LANCZOS) # Resize for display
                self.qr_photo = ImageTk.PhotoImage(img)
                self.qr_code_label.config(image=self.qr_photo)
            except Exception as e:
                logging.error(f"Error generating QR code: {e}")
                self.qr_code_label.config(image='')
                self.qr_photo = None
        else:
            self.qr_code_label.config(image='')
            self.qr_photo = None
    
    def on_model_selected(self, event):
        """Updates the LLM service model when a new model is selected in the combobox."""
        selected_model = self.model_var.get()
        self.controller.llm_service.model = selected_model
        logging.info(f"AI model set to: {selected_model}")
        self.update_status(f"AI model set to: {selected_model}")

    def update_monitoring_indicator(self, status, color="black"):
        """Updates the monitoring indicator label."""
        self.monitoring_indicator.config(text=f"Monitoring: {status}", foreground=color)
        
    def update_status(self, message):
        """Updates the status bar text."""
        self.status_bar.config(text=f"Status: {message}")
        logging.info(f"Status: {message}") # Log status updates

    def update_text_widget(self, text_widget, content):
        """Safely updates a Tkinter Text widget from any thread."""
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, content)
        text_widget.config(state="disabled")
        text_widget.see(tk.END) # Scroll to the end

    def set_response_loading_state(self, is_loading):
        """Displays a loading message in the response area."""
        self.response_text.config(state="normal")
        if is_loading:
            self.response_text.delete("1.0", tk.END)
            self.response_text.insert(tk.END, "Loading AI Response...\n", "loading_tag")
            self.response_text.tag_config("loading_tag", foreground="blue", font=("Segoe UI", 10, "italic"))
            self.response_text.see(tk.END)
        else:
            # Clear loading message if it's still there
            if self.response_text.tag_ranges("loading_tag"):
                self.response_text.delete("1.0", tk.END)
        self.response_text.config(state="disabled")

    def update_clipboard_display(self, text):
        """Updates the clipboard display area on the main thread."""
        self.update_text_widget(self.clipboard_text, text)

    def update_response_display(self, text):
        """Updates the response display area and the shared state on the main thread."""
        self.set_response_loading_state(False) # Clear loading message
        self.update_text_widget(self.response_text, text)


    def toggle_query(self):
        """Toggles the solving mode on/off via the controller."""
        new_state = self.controller.toggle_solving_mode()
        if new_state:
            self.toggle_button.config(text="Pause Solving Mode")
            self.update_status("Solving Mode ACTIVE. Monitoring clipboard...")
        else:
            self.toggle_button.config(text="Start Solving Mode") # Changed from "Start Agent Mode"
            self.update_status("Solving Mode PAUSED.")
        logging.info(f"Querying {'enabled' if new_state else 'paused'}")

    def toggle_server(self):
        """Starts or stops the Flask server via the controller."""
        try:
            is_running, server_url = self.controller.toggle_server()
            self.controller.server_running = is_running # Update controller's state
            if is_running:
                self.server_label.config(text=f"Server: Running at {server_url}")
                self.server_button.config(text="Stop Server")
                self.update_status(f"Flask server started at {server_url}")
            else:
                self.server_label.config(text="Server: Not running")
                self.server_button.config(text="Start Phone Server")
                self.update_status("Flask server stopped gracefully.")
        except Exception as e:
            logging.exception("Failed to toggle Flask server")
            self.server_label.config(text="Server: Error starting")
            self.server_button.config(text="Start Phone Server")
            self.update_status(f"Error toggling server: {e}")


    def open_settings(self):
        """Opens a settings dialog to configure the API key."""
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x150")
        settings_window.attributes('-topmost', True)

        # API Key Label and Entry
        ttk.Label(settings_window, text="OpenAI API Key:").pack(pady=(10, 5), padx=10, anchor='w')
        
        # Use the LLMService from the controller
        api_key_var = tk.StringVar(value=self.controller.llm_service.api_key if self.controller.llm_service.api_key else "")
        api_key_entry = ttk.Entry(settings_window, textvariable=api_key_var, width=50, show="*")
        api_key_entry.pack(pady=5, padx=10)

        # Show/Hide Checkbox
        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            if show_var.get():
                api_key_entry.config(show="")
            else:
                api_key_entry.config(show="*")
        
        ttk.Checkbutton(settings_window, text="Show API Key", variable=show_var, command=toggle_show).pack(anchor='w', padx=10)

        # Save Button
        def save_and_close():
            new_key = api_key_var.get().strip()
            if not new_key:
                messagebox.showerror("Error", "API Key cannot be empty.", parent=settings_window)
                return
            
            try:
                # Update .env file
                env_file = ".env"
                if not os.path.exists(env_file):
                    with open(env_file, "w") as f:
                        f.write("") # Create if missing
                
                set_key(env_file, "OPENAI_API_KEY", new_key)
                
                # Update LLMService in controller
                self.controller.llm_service.update_api_key(new_key)
                
                messagebox.showinfo("Success", "Settings saved and API key updated!", parent=settings_window)
                settings_window.destroy()
            except Exception as e:
                logging.error(f"Failed to save settings: {e}")
                messagebox.showerror("Error", f"Failed to save settings: {e}", parent=settings_window)

        ttk.Button(settings_window, text="Save", command=save_and_close).pack(pady=10)

    def on_closing(self):
        """Handles the window close event."""
        logging.info("Application closing...")
        self.update_status("Exiting...")
        
        # Stop controller's monitoring thread
        self.controller.stop_monitoring()

        # Stop Flask server if running
        if self.controller.server_running:
             server.stop_server()
             logging.info("Flask server stopped as part of application shutdown.")

        self.destroy() # Close the Tkinter window
