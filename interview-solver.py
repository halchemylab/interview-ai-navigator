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
print("Loading environment variables...")

# ===== Configuration =====
# Get API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("ERROR: OpenAI API key not found in .env file")
    raise ValueError("OpenAI API key not found in .env file")
else:
    print("OpenAI API key loaded successfully")

# Default paths and settings
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshot")
DEFAULT_PORT = 8765
# Changed hotkey to avoid system conflicts
HOTKEY_COMBINATION = {keyboard.Key.alt, keyboard.Key.shift, keyboard.KeyCode.from_char('q')}
print(f"Using hotkey combination: Alt+Shift+Q")
print(f"Screenshot directory: {SCREENSHOT_DIR}")

# ===== Initialize OpenAI client =====
openai.api_key = OPENAI_API_KEY
print("OpenAI client initialized")

# ===== Helper Functions =====
def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        print("Getting local IP address...")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"Local IP address: {ip}")
        return ip
    except Exception as e:
        print(f"Error getting local IP address: {str(e)}")
        return "127.0.0.1"  # Fallback to localhost

def ensure_directory_exists(directory):
    """Ensure that the specified directory exists."""
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory)
    else:
        print(f"Directory already exists: {directory}")

# ===== Screen Capture Functions =====
def capture_screenshot():
    """Capture a screenshot of the entire primary display."""
    print("Capturing screenshot...")
    ensure_directory_exists(SCREENSHOT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    # Capture the screenshot
    screenshot = ImageGrab.grab()
    screenshot.save(filepath)
    print(f"Screenshot saved to: {filepath}")
    
    return filepath

# ===== ChatGPT API Functions =====
def query_chatgpt(prompt):
    """Send a prompt to ChatGPT API and get the response."""
    print("Querying ChatGPT API...")
    try:
        print(f"Sending prompt: {prompt[:50]}..." if len(prompt) > 50 else f"Sending prompt: {prompt}")
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an interview assistant helping with coding problems and technical questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        print("ChatGPT API response received")
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR querying ChatGPT API: {str(e)}")
        return f"Error querying ChatGPT API: {str(e)}"

# ===== Hotkey Handler =====
class HotkeyHandler:
    def __init__(self, callback):
        self.callback = callback
        self.current_keys = set()
        self.listener = None
        self.is_active = False
        print("HotkeyHandler initialized")
        
    def on_press(self, key):
        """Handle key press events."""
        self.current_keys.add(key)
        if HOTKEY_COMBINATION.issubset(self.current_keys):
            print("Hotkey combination detected: Alt+Shift+Q")
            self.callback()
            
    def on_release(self, key):
        """Handle key release events."""
        try:
            self.current_keys.remove(key)
        except KeyError:
            pass
            
    def start(self):
        """Start the keyboard listener."""
        if not self.is_active:
            print("Starting keyboard listener...")
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            self.is_active = True
            print("Keyboard listener started")
            
    def stop(self):
        """Stop the keyboard listener."""
        if self.is_active and self.listener:
            print("Stopping keyboard listener...")
            self.listener.stop()
            self.is_active = False
            print("Keyboard listener stopped")

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
        print(f"CompanionServer initialized on port {port}")
        
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
        print("Updating companion content...")
        self.latest_data["selected_text"] = selected_text
        self.latest_data["chatgpt_response"] = chatgpt_response
        print("Companion content updated")
            
    def start(self):
        """Start the Flask server in a separate thread."""
        if not self.is_running:
            print("Starting companion server...")
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
                        .instructions {
                            background-color: #e8f4fc;
                            padding: 15px;
                            border-radius: 5px;
                            margin-bottom: 20px;
                            border-left: 4px solid #4a90e2;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Interview Solver - Companion Mode</h1>
                        
                        <div class="instructions">
                            <h3>How to Use:</h3>
                            <ol>
                                <li>Select text from your interview problem or question</li>
                                <li>Copy the text to clipboard (Ctrl+C)</li>
                                <li>Press <strong>Alt+Shift+Q</strong> to query ChatGPT</li>
                                <li>The response will appear below and in the main application</li>
                            </ol>
                            <p>This companion window is designed to be visible on a separate screen during your interview.</p>
                        </div>
                        
                        <div class="panel">
                            <div class="panel-heading">Selected Text</div>
                            <pre id="selected-text">Waiting for content... (Select text, copy it, then press Alt+Shift+Q)</pre>
                        </div>
                        
                        <div class="panel">
                            <div class="panel-heading">ChatGPT Response</div>
                            <div id="chatgpt-response">Responses will appear here after using Alt+Shift+Q hotkey...</div>
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
                
                print(f"Starting Flask server on port {self.port}...")
                self.app.run(host="0.0.0.0", port=self.port, debug=False)
                
            self.thread = threading.Thread(target=run_server)
            self.thread.daemon = True
            self.thread.start()
            self.is_running = True
            print(f"Companion server started on port {self.port}")
            
    def stop(self):
        """Stop the Flask server."""
        # Flask doesn't have a clean shutdown mechanism when run in a thread
        # We'll rely on the application exit to terminate the thread
        if self.is_running:
            print("Stopping companion server...")
            self.is_running = False
            print("Companion server stopped")
        
    def get_url(self):
        """Get the URL for the companion mode."""
        ip = get_local_ip()
        url = f"http://{ip}:{self.port}"
        print(f"Companion URL: {url}")
        return url

# ===== Main Application =====
class InterviewSolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interview Solver")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Set up components
        self.companion_server = CompanionServer()
        self.hotkey_handler = HotkeyHandler(self.handle_hotkey)
        
        print("Initializing UI...")
        # Initialize UI
        self.setup_ui()
        
        # Start the hotkey listener
        self.hotkey_handler.start()
        print("InterviewSolverApp initialized")
        
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = tk.Label(main_frame, text="Interview Solver", font=("Arial", 18, "bold"))
        header_label.pack(pady=(0, 20))
        
        # Instructions frame
        instructions_frame = tk.LabelFrame(main_frame, text="Instructions")
        instructions_frame.pack(fill=tk.X, pady=10)
        
        instructions_text = """
How to use Interview Solver:
1. Start the Companion Mode to display responses on a separate screen (optional)
2. Select text from your interview problem or question
3. Copy the text to clipboard (Ctrl+C)
4. Press Alt+Shift+Q to query ChatGPT
5. View the response in the application and companion window (if started)
        """
        
        instructions_label = tk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT, anchor="w")
        instructions_label.pack(fill=tk.X, padx=10, pady=10)
        
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
        text_frame = tk.LabelFrame(main_frame, text="Selected Text (Alt+Shift+Q to query)")
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
        self.status_var.set("Ready - Press Alt+Shift+Q after copying text to query ChatGPT")
        
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
            error_msg = f"Error capturing screenshot: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.status_var.set(error_msg)
            messagebox.showerror("Error", f"Failed to capture screenshot: {str(e)}")
            
    def toggle_companion_mode(self):
        """Toggle the companion mode on/off."""
        if not self.companion_server.is_running:
            # Start companion mode
            try:
                print("Starting companion mode...")
                self.companion_server.start()
                url = self.companion_server.get_url()
                self.url_var.set(url)
                self.companion_btn.config(text="Stop Companion Mode")
                self.status_var.set(f"Companion mode started at {url}")
                
                # Open the URL in the default browser
                print(f"Opening URL in browser: {url}")
                webbrowser.open(url)
            except Exception as e:
                error_msg = f"Error starting companion mode: {str(e)}"
                print(f"ERROR: {error_msg}")
                self.status_var.set(error_msg)
                messagebox.showerror("Error", f"Failed to start companion mode: {str(e)}")
        else:
            # Stop companion mode
            try:
                print("Stopping companion mode...")
                self.companion_server.stop()
                self.url_var.set("Companion mode not started")
                self.companion_btn.config(text="Start Companion Mode")
                self.status_var.set("Companion mode stopped")
            except Exception as e:
                error_msg = f"Error stopping companion mode: {str(e)}"
                print(f"ERROR: {error_msg}")
                self.status_var.set(error_msg)
            
    def handle_hotkey(self):
        """Handle the global hotkey press (Alt+Shift+Q)."""
        # Get the selected text from clipboard
        print("Hotkey triggered, getting text from clipboard...")
        selected_text = pyperclip.paste()
        
        if selected_text:
            print(f"Text found in clipboard ({len(selected_text)} characters)")
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
                    print("Updating companion mode with new content")
                    self.companion_server.update_content(selected_text, response)
            except Exception as e:
                error_msg = f"Error querying ChatGPT: {str(e)}"
                print(f"ERROR: {error_msg}")
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(tk.END, error_msg)
                self.status_var.set(error_msg)
        else:
            print("No text found in clipboard")
            self.status_var.set("No text selected. Copy text to clipboard before using hotkey.")
            messagebox.showinfo("No Text Selected", "Please select and copy (Ctrl+C) text before using the Alt+Shift+Q hotkey.")
            
    def on_close(self):
        """Handle application close event."""
        print("Application closing...")
        try:
            self.hotkey_handler.stop()
            self.companion_server.stop()
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
        self.root.destroy()
        print("Application closed")

# ===== Main Entry Point =====
def main():
    print("Starting Interview Solver application...")
    # Ensure the screenshots directory exists
    ensure_directory_exists(SCREENSHOT_DIR)
    
    # Create and start the GUI application
    root = tk.Tk()
    app = InterviewSolverApp(root)
    
    # Set up close handler
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Display startup message
    print("=" * 50)
    print("Interview Solver is running")
    print(f"Hotkey combination: Alt+Shift+Q")
    print("=" * 50)
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()