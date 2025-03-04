import os
import threading
import tkinter as tk
from tkinter import ttk
import pyperclip
import openai
from dotenv import load_dotenv
from flask import Flask, jsonify
import socket

# Load API key from .env
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in .env file")

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask server
app = Flask(__name__)
latest_response = ""
server_thread = None
server_running = False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip

@app.route('/response', methods=['GET'])
def get_response():
    return jsonify({"response": latest_response})

class SimpleChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Interview AI Navigator")
        self.geometry("400x600")
        self.attributes('-topmost', True)  # Always on top
        self.last_clipboard = ""
        self.query_enabled = False  # Control querying
        self.server_enabled = False # Server control
        self.polling_rate = 1000  # Default polling rate (ms)
        
        # Model selector
        self.model_var = tk.StringVar(value="gpt-4o-mini")
        model_frame = tk.Frame(self)
        tk.Label(model_frame, text="Select AI Model:").pack(side=tk.LEFT, padx=(0, 10))
        model_selector = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly",
                                      values=["gpt-4o-mini", "gpt-4o", "o1"])
        model_selector.pack(side=tk.LEFT)
        model_frame.pack(pady=10)
        
        # Clipboard text display
        clip_frame = tk.LabelFrame(self, text="Clipboard Text")
        self.clipboard_text = tk.Text(clip_frame, height=8, wrap=tk.WORD, state="disabled")
        self.clipboard_text.pack(fill=tk.BOTH, padx=10, pady=10)
        clip_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        # ChatGPT response display
        resp_frame = tk.LabelFrame(self, text="Coding Hints")
        self.response_text = tk.Text(resp_frame, height=15, wrap=tk.WORD, state="disabled")
        self.response_text.pack(fill=tk.BOTH, padx=10, pady=10)
        resp_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        
        # Query Toggle Button
        self.toggle_button = tk.Button(self, text="Start Solving Mode", command=self.toggle_query)
        
        # Server Toggle Button
        self.server_button = tk.Button(self, text="Start Server for Phone Display", command=self.toggle_server)
        self.server_button.pack(pady=5)
        self.toggle_button.pack(pady=5)
        
        # Server URL Label
        self.server_label = tk.Label(self, text="Server: Not running", anchor=tk.W)
        self.server_label.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Start clipboard monitoring
        self.after(self.polling_rate, self.check_clipboard)

    def check_clipboard(self):
        new_text = pyperclip.paste()
        if new_text and new_text != self.last_clipboard:
            self.last_clipboard = new_text
            self.update_clipboard_display(new_text)
            print("New clipboard text detected")
            if self.query_enabled:
                thread = threading.Thread(target=self.query_api, args=(new_text,), daemon=True)
                thread.start()
        self.after(self.polling_rate, self.check_clipboard)

    def update_clipboard_display(self, text):
        self.clipboard_text.config(state="normal")
        self.clipboard_text.delete("1.0", tk.END)
        self.clipboard_text.insert(tk.END, text)
        self.clipboard_text.config(state="disabled")

    def update_response_display(self, text):
        global latest_response
        latest_response = text  # Update global response for Flask server
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert(tk.END, text)
        self.response_text.config(state="disabled")

    def query_api(self, prompt):
        model = self.model_var.get()
        messages = [
            {"role": "system", "content": "Provide simple commenting, hints, and code response only."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            output = response.choices[0].message.content
            print("API response sent")
            print(f"Response: {output}")
            self.after(0, lambda: self.update_response_display(output))
        except Exception as e:
            output = f"Error querying ChatGPT API: {str(e)}"
            print(f"Error: {str(e)}")
            self.after(0, lambda: self.update_response_display(output))
    
    def toggle_query(self):
        self.query_enabled = not self.query_enabled
        if self.query_enabled:
            self.toggle_button.config(text="Pause Agent Mode")
        else:
            self.toggle_button.config(text="Start Agent Mode")
        print(f"Querying {'enabled' if self.query_enabled else 'paused'}")
    
    def toggle_server(self):
        global server_running, server_thread
        if server_running:
            self.server_label.config(text="Server: Not running")
            self.server_button.config(text="Start Server for Phone Display")
            server_running = False
        else:
            self.server_label.config(text=f"Server: Running at http://{get_local_ip()}:5001/response")
            self.server_button.config(text="Stop Server")
            server_running = True
            server_thread = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5001, "debug": False, "use_reloader": False}, daemon=True)
            server_thread.start()

def main():
    app = SimpleChatApp()
    app.mainloop()

if __name__ == "__main__":
    main()