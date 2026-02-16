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
from ocr_service import RegionSelector
from state import global_state
import qrcode
from PIL import Image, ImageTk # Import Pillow modules
import re
from pygments import lexers, highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.styles import get_style_by_name

class SimpleChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Interview AI Navigator")
        self.geometry("450x800") # Slightly larger for history
        self.attributes('-topmost', True)  # Always on top

        # --- Setup Style ---
        self.style = ttk.Style()
        self._setup_dark_theme()

        # --- Initialize Controller ---
        self.controller = InterviewController(
            update_callback=lambda text: self.after(0, self.update_response_display, text),
            clipboard_callback=lambda text: self.after(0, self.update_clipboard_display, text),
            status_callback=lambda text: self.after(0, self.update_status, text),
            monitoring_status_callback=lambda status, color: self.after(0, self.update_monitoring_indicator, status, color),
            response_loading_callback=lambda is_loading: self.after(0, self.set_response_loading_state, is_loading),
            qr_code_callback=lambda url: self.after(0, self.update_qr_code, url),
            visibility_callback=lambda: self.after(0, self.toggle_visibility),
            solving_mode_callback=lambda enabled: self.after(0, self.update_solving_mode_ui, enabled),
            ocr_callback=lambda: self.after(0, self.open_region_selector)
        )
        
        if not self.controller.llm_service.api_key:
             messagebox.showerror("Error", "OpenAI API key not found.\nPlease create a .env file with OPENAI_API_KEY=your_key or configure it in Settings.")

        # --- Window State ---
        self.is_hidden = False
        self.history_index = -1 # -1 means viewing current/latest stream

        # --- OpenAI Model ---
        self.model_var = tk.StringVar(value="gpt-4o-mini") # Default model

        # --- Build UI ---
        self._create_widgets()

        # --- Start Processes ---
        self.update_status("Ready. Press 'Start Solving Mode' to begin.")
        self.controller.start_monitoring() 
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_dark_theme(self):
        """Configures a modern dark theme for the application."""
        self.colors = {
            'bg': '#121212',
            'fg': '#e0e0e0',
            'text_bg': '#1e1e1e',
            'accent': '#4CAF50',
            'border': '#333333',
            'header': '#888888'
        }
        
        self.configure(bg=self.colors['bg'])
        
        self.style.theme_use('clam')
        
        self.style.configure("TFrame", background=self.colors['bg'])
        self.style.configure("TLabel", background=self.colors['bg'], foreground=self.colors['fg'], font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=self.colors['bg'], foreground=self.colors['header'], bordercolor=self.colors['border'])
        self.style.configure("TLabelframe.Label", background=self.colors['bg'], foreground=self.colors['accent'], font=("Segoe UI", 10, "bold"))
        
        self.style.configure("TButton", 
                            background=self.colors['accent'], 
                            foreground="white", 
                            font=("Segoe UI", 9, "bold"),
                            borderwidth=0)
        self.style.map("TButton", 
                      background=[('active', '#45a049'), ('pressed', '#3d8b40')],
                      foreground=[('disabled', '#888888')])
        
        self.style.configure("TCombobox", fieldbackground=self.colors['text_bg'], background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure("TCheckbutton", background=self.colors['bg'], foreground=self.colors['fg'])

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
        
        # Interview Mode Toggle
        self.interview_mode_var = tk.BooleanVar(value=True) # Default on
        ttk.Checkbutton(model_frame, text="Step-by-Step Interview Mode", variable=self.interview_mode_var, command=self.toggle_interview_mode).pack(side=tk.LEFT, padx=(15, 0))
        
        model_frame.pack(pady=(0, 10), anchor='w')

        # --- Opacity Control ---
        opacity_frame = ttk.Frame(main_frame)
        ttk.Label(opacity_frame, text="Window Opacity:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 10))
        self.opacity_scale = ttk.Scale(opacity_frame, from_=0.2, to=1.0, value=1.0, orient=tk.HORIZONTAL, command=self.update_opacity, length=150)
        self.opacity_scale.pack(side=tk.LEFT)
        opacity_frame.pack(fill=tk.X, pady=(0, 10))

        # Monitoring Indicator
        self.monitoring_indicator = ttk.Label(main_frame, text="Monitoring: Inactive", anchor=tk.W, font=("Segoe UI", 9, "italic"))
        self.monitoring_indicator.pack(fill=tk.X, pady=(0, 5))

        # --- Hotkey Reference ---
        hotkey_frame = ttk.LabelFrame(main_frame, text="Stealth Hotkeys")
        hotkey_grid = ttk.Frame(hotkey_frame, padding="5")
        hotkey_grid.pack(fill=tk.X)

        keys = [
            ("Alt + X", "Silent Full Capture"),
            ("Alt + Shift + S", "Region OCR Select"),
            ("Alt + H", "Hide / Show App"),
            ("Alt + Q", "Toggle Auto-Solve")
        ]

        for i, (key, desc) in enumerate(keys):
            row, col = divmod(i, 2)
            ttk.Label(hotkey_grid, text=key, font=("Segoe UI", 9, "bold")).grid(row=row, column=col*2, sticky=tk.W, padx=(5, 2))
            ttk.Label(hotkey_grid, text=f": {desc}", font=("Segoe UI", 9)).grid(row=row, column=col*2+1, sticky=tk.W, padx=(0, 15))

        hotkey_frame.pack(fill=tk.X, pady=5)

        # Clipboard Text Display
        clip_frame = ttk.LabelFrame(main_frame, text="Clipboard Content")
        # Use scrolledtext for automatic scrollbars
        self.clipboard_text = scrolledtext.ScrolledText(clip_frame, height=8, wrap=tk.WORD, state="disabled", 
                                                        relief=tk.FLAT, bg=self.colors['text_bg'], 
                                                        fg=self.colors['fg'], insertbackground=self.colors['fg'])
        self.clipboard_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        clip_frame.pack(fill=tk.BOTH, pady=5)

        # ChatGPT Response Display
        resp_frame = ttk.LabelFrame(main_frame, text="Coding Hints / Response")
        
        # History Navigation Bar
        nav_frame = ttk.Frame(resp_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(2, 0))
        
        self.prev_btn = ttk.Button(nav_frame, text="< Prev", width=8, command=self.view_previous_history)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.history_label = ttk.Label(nav_frame, text="Latest Hint", font=("Segoe UI", 9, "bold"), foreground=self.colors['accent'])
        self.history_label.pack(side=tk.LEFT, expand=True)
        
        self.next_btn = ttk.Button(nav_frame, text="Next >", width=8, command=self.view_next_history, state="disabled")
        self.next_btn.pack(side=tk.RIGHT)

        self.response_text = scrolledtext.ScrolledText(resp_frame, height=15, wrap=tk.WORD, state="disabled", 
                                                       relief=tk.FLAT, bg=self.colors['text_bg'], 
                                                       fg=self.colors['fg'], insertbackground=self.colors['fg'])
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        resp_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- Buttons Frame ---
        button_frame = ttk.Frame(main_frame)
        self.toggle_button = ttk.Button(button_frame, text="Start Solving Mode", command=self.toggle_query, width=20)
        self.toggle_button.pack(side=tk.LEFT, padx=5)

        self.ocr_button = ttk.Button(button_frame, text="Region OCR (Alt+Shift+S)", command=self.open_region_selector, width=25)
        self.ocr_button.pack(side=tk.LEFT, padx=5)

        self.silent_ocr_button = ttk.Button(button_frame, text="Silent Capture (Alt+X)", command=self.trigger_silent_ocr, width=25)
        self.silent_ocr_button.pack(side=tk.LEFT, padx=5)

        self.server_button = ttk.Button(button_frame, text="Start Phone Server", command=self.toggle_server, width=20)
        self.server_button.pack(side=tk.LEFT, padx=5)

        self.settings_button = ttk.Button(button_frame, text="Settings", command=self.open_settings, width=15)
        self.settings_button.pack(side=tk.LEFT, padx=5)

        self.test_connection_button = ttk.Button(button_frame, text="Test Phone Connection", command=self.test_phone_connection, width=20)
        self.test_connection_button.pack(side=tk.LEFT, padx=5)
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
    
    def update_opacity(self, value):
        """Updates the window opacity based on the scale value."""
        self.attributes('-alpha', float(value))

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
        """Safely updates a Tkinter Text widget with syntax highlighting for code blocks."""
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        
        # Define tags for code blocks
        text_widget.tag_config("code_block", background="#2d2d2d", font=("Consolas", 10))
        text_widget.tag_config("bold", font=("Segoe UI", 10, "bold"), foreground="#4CAF50")
        
        # Simple regex to split content into code blocks and normal text
        parts = re.split(r'(```[\s\S]*?```)', content)
        
        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                # Code block
                code_content = part[3:-3].strip()
                # Try to extract language
                lines = code_content.split('\n')
                lang = "python" # Default
                if lines and not lines[0].startswith(' ') and len(lines[0]) < 20:
                    lang = lines[0].strip()
                    code_content = '\n'.join(lines[1:])
                
                start_index = text_widget.index(tk.INSERT)
                text_widget.insert(tk.END, code_content + "\n", "code_block")
                
                # Apply basic syntax highlighting within the code block if pygments is available
                self._apply_syntax_highlighting(text_widget, code_content, lang, start_index)
            else:
                # Normal text - handle basic bolding
                sub_parts = re.split(r'(\*\*[\s\S]*?\*\*)', part)
                for sub_part in sub_parts:
                    if sub_part.startswith("**") and sub_part.endswith("**"):
                        text_widget.insert(tk.END, sub_part[2:-2], "bold")
                    else:
                        text_widget.insert(tk.END, sub_part)

        text_widget.config(state="disabled")
        text_widget.see(tk.END)

    def _apply_syntax_highlighting(self, text_widget, code, lang, start_index):
        """Applies syntax highlighting to a code block using Pygments tokens."""
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except:
            lexer = guess_lexer(code)
        
        # Tokenize
        tokens = list(lexer.get_tokens(code))
        
        # Map pygments token types to colors (Dark mode friendly)
        color_map = {
            'Token.Keyword': '#569cd6',
            'Token.Name.Function': '#dcdcaa',
            'Token.Name.Class': '#4ec9b0',
            'Token.String': '#ce9178',
            'Token.Comment': '#6a9955',
            'Token.Operator': '#d4d4d4',
            'Token.Number': '#b5cea8',
        }

        current_pos = start_index
        for token_type, value in tokens:
            # Tkinter uses "line.char" format
            t_type_str = str(token_type)
            color = None
            for key, val in color_map.items():
                if t_type_str.startswith(key):
                    color = val
                    break
            
            if color:
                tag_name = f"syntax_{color.replace('#', '')}"
                text_widget.tag_config(tag_name, foreground=color)
                
                # Calculate end position
                end_pos = text_widget.index(f"{current_pos} + {len(value)}c")
                text_widget.tag_add(tag_name, current_pos, end_pos)
                current_pos = end_pos
            else:
                current_pos = text_widget.index(f"{current_pos} + {len(value)}c")

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
        self.history_index = -1 # Reset to current when a new response starts streaming
        self._update_nav_buttons()
        self.set_response_loading_state(False) # Clear loading message
        self.update_text_widget(self.response_text, text)

    def view_previous_history(self):
        """Shows the previous response from history."""
        history = global_state.history
        if not history:
            return

        if self.history_index == -1:
            self.history_index = len(history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
        
        self._show_historical_response()

    def view_next_history(self):
        """Shows the next response from history, or returns to current."""
        history = global_state.history
        if self.history_index == -1:
            return

        if self.history_index < len(history) - 1:
            self.history_index += 1
            self._show_historical_response()
        else:
            self.history_index = -1
            self.update_response_display(global_state.latest_response)

    def _show_historical_response(self):
        """Displays the response at the current history index."""
        history = global_state.history
        if 0 <= self.history_index < len(history):
            content = history[self.history_index]
            self.update_text_widget(self.response_text, content)
            self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Updates the navigation button states and label."""
        history = global_state.history
        
        if self.history_index == -1:
            self.history_label.config(text="Latest Hint", foreground=self.colors['accent'])
            self.next_btn.config(state="disabled")
            self.prev_btn.config(state="normal" if history else "disabled")
        else:
            self.history_label.config(text=f"History: {self.history_index + 1} / {len(history)}", foreground="orange")
            self.next_btn.config(state="normal")
            self.prev_btn.config(state="normal" if self.history_index > 0 else "disabled")

    def open_region_selector(self):
        """Opens the transparent overlay for region selection."""
        RegionSelector(callback=self.controller.process_ocr_region)

    def trigger_silent_ocr(self):
        """Triggers the silent OCR in the controller."""
        self.controller.trigger_silent_ocr()

    def test_phone_connection(self):
        """Sends a test message to the Flask server to check phone connection."""
        if not self.controller.server_running:
            self.update_status("Server not running. Start the phone server first.")
            messagebox.showwarning("Server Not Running", "Please start the phone server before testing the connection.")
            return

        self.update_status("Sending test message to phone...")
        # Run in a thread to avoid blocking GUI
        threading.Thread(target=self._run_test_connection_thread, daemon=True).start()

    def _run_test_connection_thread(self):
        try:
            success = self.controller.send_test_message_to_server()
            if success:
                self.after(0, lambda: self.update_status("Test message sent successfully! Check your phone."))
                self.after(0, lambda: messagebox.showinfo("Connection Test", "Test message sent successfully! Check your phone."))
            else:
                self.after(0, lambda: self.update_status("Failed to send test message. Is the phone connected and server accessible?"))
                self.after(0, lambda: messagebox.showerror("Connection Test Failed", "Failed to send test message. Is the phone connected and server accessible?"))
        except Exception as e:
            logging.exception("Error during phone connection test")
            self.after(0, lambda: self.update_status(f"Error during test: {e}"))
            self.after(0, lambda: messagebox.showerror("Connection Test Error", f"An error occurred: {e}"))

    def toggle_interview_mode(self):
        """Toggles the interview mode in the controller."""
        enabled = self.interview_mode_var.get()
        self.controller.toggle_interview_mode(enabled)

    def toggle_query(self):
        """Toggles the solving mode on/off via the controller."""
        self.controller.toggle_solving_mode()

    def update_solving_mode_ui(self, enabled):
        """Updates the UI button and status based on solving mode state."""
        if enabled:
            self.toggle_button.config(text="Pause Solving Mode")
            self.update_status("Solving Mode ACTIVE. Monitoring clipboard...")
        else:
            self.toggle_button.config(text="Start Solving Mode")
            self.update_status("Solving Mode PAUSED.")
        logging.info(f"Solving mode {'enabled' if enabled else 'paused'}")

    def toggle_visibility(self):
        """Toggles the main window visibility."""
        if self.is_hidden:
            self.deiconify()
            self.attributes('-topmost', True)
            self.is_hidden = False
            logging.info("Window shown.")
        else:
            self.withdraw()
            self.is_hidden = True
            logging.info("Window hidden.")

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
