import os
import sys
import time
import json
import threading
import socket
import pyperclip
from PIL import ImageGrab
from pynput import keyboard
from flask import Flask, render_template, jsonify, request
import tkinter as tk
from tkinter import messagebox, scrolledtext
import openai
import webbrowser
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ===== Configuration =====
# Get API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in .env file")

# Default paths and settings
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshot")
DEFAULT_PORT = 8765
HOTKEY_COMBINATION = {keyboard.Key.ctrl, keyboard.KeyCode.from_char('c')}  # Changed to Ctrl+C/Cmd+C
STOP_SERVER_COMBINATION = {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char('x')}  # Added Ctrl+Shift+X to stop server

# ===== Initialize OpenAI client =====
openai.api_key = OPENAI_API_KEY

# ===== Helper Functions =====
def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost

def ensure_directory_exists(directory):
    """Ensure that the specified directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)

# ===== Screen Capture Functions =====
def capture_screenshot():
    """Capture a screenshot of the entire primary display."""
    ensure_directory_exists(SCREENSHOT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    # Capture the screenshot
    screenshot = ImageGrab.grab()
    screenshot.save(filepath)
    
    return filepath

# ===== ChatGPT API Functions =====
def query_chatgpt(prompt):
    """Send a prompt to ChatGPT API and get the response."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an interview assistant helping with coding problems and technical questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying ChatGPT API: {str(e)}"

# ===== Hotkey Handler =====
class HotkeyHandler:
    def __init__(self, callback, stop_server_callback):  # Added stop_server_callback
        self.callback = callback
        self.stop_server_callback = stop_server_callback  # Added stop server callback
        self.current_keys = set()
        self.listener = None
        self.is_active = False
        
    def on_press(self, key):
        """Handle key press events."""
        self.current_keys.add(key)
        if HOTKEY_COMBINATION.issubset(self.current_keys):
            self.callback()
        elif STOP_SERVER_COMBINATION.issubset(self.current_keys):  # Added stop server hotkey check
            self.stop_server_callback()
            
    def on_release(self, key):
        """Handle key release events."""
        try:
            self.current_keys.remove(key)
        except KeyError:
            pass
            
    def start(self):
        """Start the keyboard listener."""
        if not self.is_active:
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            self.is_active = True
            
    def stop(self):
        """Stop the keyboard listener."""
        if self.is_active and self.listener:
            self.listener.stop()
            self.is_active = False

# ===== Flask Web Server =====
class CompanionServer:
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.app = Flask(__name__)
        self.thread = None
        self.is_running = False
        self.latest_data = {
            "selected_text": "",
            "chatgpt_response": ""
        }
        
        # Define Flask routes
        @self.app.route('/')
        def index():
            return render_template('companion.html')
            
        @self.app.route('/api/data')
        def get_data():
            return jsonify(self.latest_data)
            
        @self.app.route('/api/update', methods=['POST'])
        def update_data():
            data = request.json
            self.latest_data.update(data)
            return jsonify({"status": "success"})
            
    def update_content(self, selected_text, chatgpt_response):
        """Update the content to be displayed on the companion screen."""
        self.latest_data["selected_text"] = selected_text
        self.latest_data["chatgpt_response"] = chatgpt_response
            
    def start(self):
        """Start the Flask server in a separate thread."""
        if not self.is_running:
            def run_server():
                # Create templates directory and HTML file
                templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
                ensure_directory_exists(templates_dir)
                
                companion_html = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Interview Solver - Companion Mode</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            margin: 0;
                            padding: 20px;
                            background-color: #f5f5f5;
                        }
                        .container {
                            max-width: 1200px;
                            margin: 0 auto;
                            background-color: white;
                            padding: 20px;
                            border-radius: 5px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }
                        h1, h2 {
                            color: #333;
                        }
                        .panel {
                            margin-bottom: 20px;
                            border: 1px solid #ddd;
                            border-radius: 5px;
                            padding: 15px;
                        }
                        .panel-heading {
                            font-weight: bold;
                            margin-bottom: 10px;
                            padding-bottom: 5px;
                            border-bottom: 1px solid #eee;
                        }
                        pre {
                            background-color: #f8f8f8;
                            padding: 10px;
                            border-radius: 3px;
                            overflow-x: auto;
                        }
                        .timestamp {
                            color: #999;
                            font-size: 0.8em;
                            text-align: right;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Interview Solver - Companion Mode</h1>
                        <p>This screen displays the selected text and ChatGPT responses from the main application.</p>
                        
                        <div class="panel">
                            <div class="panel-heading">Selected Text</div>
                            <pre id="selected-text">Waiting for content...</pre>
                        </div>
                        
                        <div class="panel">
                            <div class="panel-heading">ChatGPT Response</div>
                            <div id="chatgpt-response">Waiting for content...</div>
                        </div>
                        
                        <div class="timestamp" id="timestamp"></div>
                    </div>

                    <script>
                        // Poll for updates every second
                        function fetchData() {
                            fetch('/api/data')
                                .then(response => response.json())
                                .then(data => {
                                    if (data.selected_text) {
                                        document.getElementById('selected-text').textContent = data.selected_text;
                                    }
                                    if (data.chatgpt_response) {
                                        const responseEl = document.getElementById('chatgpt-response');
                                        // Format code blocks with <pre> tags
                                        let formattedResponse = data.chatgpt_response;
                                        
                                        // Try to identify code blocks (text between ``` markers)
                                        const codeBlockRegex = /```([\s\S]*?)```/g;
                                        formattedResponse = formattedResponse.replace(codeBlockRegex, 
                                            (match, code) => `<pre>${code}</pre>`);
                                        
                                        responseEl.innerHTML = formattedResponse;
                                    }
                                    document.getElementById('timestamp').textContent = 
                                        'Last updated: ' + new Date().toLocaleTimeString();
                                })
                                .catch(error => console.error('Error fetching data:', error));
                        }

                        // Initial fetch and set interval
                        fetchData();
                        setInterval(fetchData, 1000);
                    </script>
                </body>
                </html>
                """
                
                with open(os.path.join(templates_dir, "companion.html"), "w") as f:
                    f.write(companion_html)
                
                self.app.run(host="0.0.0.0", port=self.port, debug=False)
                
            self.thread = threading.Thread(target=run_server)
            self.thread.daemon = True
            self.thread.start()
            self.is_running = True
            
    def stop(self):
        """Stop the Flask server."""
        # Flask doesn't have a clean shutdown mechanism when run in a thread
        # We'll rely on the application exit to terminate the thread
        self.is_running = False
        
    def get_url(self):
        """Get the URL for the companion mode."""
        ip = get_local_ip()
        return f"http://{ip}:{self.port}"

# ===== Main Application =====
class InterviewSolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interview Solver")
        self.root.geometry("800x800")  # Increased height to 800px
        self.root.minsize(800, 800)  # Updated minimum size
        
        # Set up components
        self.companion_server = CompanionServer()
        self.hotkey_handler = HotkeyHandler(self.handle_hotkey, self.stop_companion_server)  # Added stop server callback
        
        # Initialize UI
        self.setup_ui()
        
        # Start the hotkey listener
        self.hotkey_handler.start()

    def stop_companion_server(self):
        """Stop the companion server via hotkey."""
        if self.companion_server.is_running:
            self.toggle_companion_mode()
            self.status_var.set("Companion server stopped via hotkey (Ctrl+Shift+X)")
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with instructions
        header_label = tk.Label(main_frame, text="Interview Solver", font=("Arial", 18, "bold"))
        header_label.pack(pady=(0, 5))
        
        instructions = "Hotkeys:\nCtrl/Cmd+C: Query selected text\nCtrl+Shift+X: Stop companion server"
        instructions_label = tk.Label(main_frame, text=instructions, justify=tk.LEFT)
        instructions_label.pack(pady=(0, 15))

        # Buttons frame
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.capture_btn = tk.Button(buttons_frame, text="Capture Screen", command=self.handle_capture_screen)
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        self.companion_btn = tk.Button(buttons_frame, text="Start Companion Mode", command=self.toggle_companion_mode)
        self.companion_btn.pack(side=tk.LEFT, padx=5)
        
        # URL display
        url_frame = tk.LabelFrame(main_frame, text="Companion Mode URL")
        url_frame.pack(fill=tk.X, pady=10)
        
        self.url_var = tk.StringVar()
        self.url_var.set("Companion mode not started")
        
        url_entry = tk.Entry(url_frame, textvariable=self.url_var, state="readonly")
        url_entry.pack(fill=tk.X, padx=10, pady=10)
        
        # Selected text frame
        text_frame = tk.LabelFrame(main_frame, text="Selected Text (Ctrl/Cmd C to query)")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.selected_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=6)
        self.selected_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ChatGPT response frame
        response_frame = tk.LabelFrame(main_frame, text="ChatGPT Response")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.response_text = scrolledtext.ScrolledText(response_frame, wrap=tk.WORD, height=10)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def handle_capture_screen(self):
        """Handle the Capture Screen button click."""
        self.status_var.set("Capturing screenshot...")
        self.root.update()
        
        try:
            filepath = capture_screenshot()
            self.status_var.set(f"Screenshot saved to: {filepath}")
            messagebox.showinfo("Screenshot Captured", f"Screenshot saved to:\n{filepath}")
        except Exception as e:
            self.status_var.set(f"Error capturing screenshot: {str(e)}")
            messagebox.showerror("Error", f"Failed to capture screenshot: {str(e)}")
            
    def toggle_companion_mode(self):
        """Toggle the companion mode on/off."""
        if not self.companion_server.is_running:
            # Start companion mode
            try:
                self.companion_server.start()
                url = self.companion_server.get_url()
                self.url_var.set(url)
                self.companion_btn.config(text="Stop Companion Mode")
                self.status_var.set(f"Companion mode started at {url}")
                
                # Open the URL in the default browser
                webbrowser.open(url)
            except Exception as e:
                self.status_var.set(f"Error starting companion mode: {str(e)}")
                messagebox.showerror("Error", f"Failed to start companion mode: {str(e)}")
        else:
            # Stop companion mode
            try:
                self.companion_server.stop()
                self.url_var.set("Companion mode not started")
                self.companion_btn.config(text="Start Companion Mode")
                self.status_var.set("Companion mode stopped")
            except Exception as e:
                self.status_var.set(f"Error stopping companion mode: {str(e)}")
            
    def handle_hotkey(self):
        """Handle the global hotkey press (Ctrl/Cmd+C)."""
        # Get the selected text from clipboard
        selected_text = pyperclip.paste()
        
        if selected_text:
            # Update the UI
            self.selected_text.delete(1.0, tk.END)
            self.selected_text.insert(tk.END, selected_text)
            
            self.status_var.set("Querying ChatGPT...")
            self.root.update()
            
            # Query ChatGPT
            try:
                response = query_chatgpt(selected_text)
                
                # Update the UI
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(tk.END, response)
                self.status_var.set("ChatGPT response received")
                
                # Update companion mode if running
                if self.companion_server.is_running:
                    self.companion_server.update_content(selected_text, response)
            except Exception as e:
                error_msg = f"Error querying ChatGPT: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(tk.END, error_msg)
                self.status_var.set(error_msg)
        else:
            self.status_var.set("No text selected. Copy text to clipboard before using hotkey.")
            
    def on_close(self):
        """Handle application close event."""
        try:
            self.hotkey_handler.stop()
            self.companion_server.stop()
        except:
            pass
        self.root.destroy()

# ===== Main Entry Point =====
def main():
    # Ensure the screenshots directory exists
    ensure_directory_exists(SCREENSHOT_DIR)
    
    # Create and start the GUI application
    root = tk.Tk()
    app = InterviewSolverApp(root)
    
    # Set up close handler
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()
