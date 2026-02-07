import logging
import tkinter as tk
from tkinter import messagebox
from gui import SimpleChatApp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        app = SimpleChatApp()
        app.mainloop()
    except Exception as e:
        logging.exception("Fatal error during application startup or runtime.")
        # Optionally show a simple error popup if Tkinter is available
        try:
            root = tk.Tk()
            root.withdraw() # Hide the main window
            messagebox.showerror("Fatal Error", f"An critical error occurred:\n\n{e}\n\nCheck logs for details.")
            root.destroy()
        except tk.TclError:
            print(f"FATAL ERROR (Tkinter unavailable?): {e}")

if __name__ == "__main__":
    main()

