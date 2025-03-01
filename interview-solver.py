import os
import threading
import tkinter as tk
from tkinter import ttk
import pyperclip
import openai
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in .env file")
openai.api_key = OPENAI_API_KEY

class SimpleChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatGPT Auto-Query")
        self.geometry("800x600")
        self.last_clipboard = ""

        # Model selector (using officially supported models)
        self.model_var = tk.StringVar(value="gpt-3.5-turbo")
        model_frame = tk.Frame(self)
        tk.Label(model_frame, text="Select Model:").pack(side=tk.LEFT, padx=(0, 10))
        model_selector = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly",
                                      values=["gpt-3.5-turbo", "gpt-4"])
        model_selector.pack(side=tk.LEFT)
        model_frame.pack(pady=10)

        # Clipboard text display (read-only)
        clip_frame = tk.LabelFrame(self, text="Clipboard Text")
        self.clipboard_text = tk.Text(clip_frame, height=8, wrap=tk.WORD, state="disabled")
        self.clipboard_text.pack(fill=tk.BOTH, padx=10, pady=10)
        clip_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # ChatGPT response display (read-only)
        resp_frame = tk.LabelFrame(self, text="ChatGPT Response")
        self.response_text = tk.Text(resp_frame, height=15, wrap=tk.WORD, state="disabled")
        self.response_text.pack(fill=tk.BOTH, padx=10, pady=10)
        resp_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)

        # Status label
        self.status_label = tk.Label(self, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Start polling the clipboard
        self.after(1000, self.check_clipboard)

    def check_clipboard(self):
        """Poll the clipboard and trigger an API call if new text is detected."""
        new_text = pyperclip.paste()
        if new_text and new_text != self.last_clipboard:
            self.last_clipboard = new_text
            self.update_clipboard_display(new_text)
            threading.Thread(target=self.query_api, args=(new_text,), daemon=True).start()
        self.after(1000, self.check_clipboard)

    def update_clipboard_display(self, text):
        self.clipboard_text.config(state="normal")
        self.clipboard_text.delete("1.0", tk.END)
        self.clipboard_text.insert(tk.END, text)
        self.clipboard_text.config(state="disabled")

    def update_response_display(self, text):
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert(tk.END, text)
        self.response_text.config(state="disabled")

    def query_api(self, prompt):
        """Send the clipboard text to the ChatGPT API and update the UI with the response."""
        self.after(0, lambda: self.status_label.config(text="Querying ChatGPT API..."))
        model = self.model_var.get()
        messages = [
            {"role": "system", "content": "Provide simple commenting and code response only."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            output = response.choices[0].message.content
        except Exception as e:
            output = f"Error querying ChatGPT API: {str(e)}"
        self.after(0, lambda: self.update_response_display(output))
        self.after(0, lambda: self.status_label.config(text="Response received"))

def main():
    app = SimpleChatApp()
    app.mainloop()

if __name__ == "__main__":
    main()
