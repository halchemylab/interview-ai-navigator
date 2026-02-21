import tkinter as tk
import pyautogui
from PIL import Image
#import easyocr
import threading
import logging
import numpy as np

class OCRService:
    def __init__(self):
        self.reader = None
        self._initialize_reader()
    
    def _validate_image(self, image):
        """Validates that image is a valid PIL Image.
        
        Args:
            image: Object to validate as PIL Image
            
        Returns:
            bool: True if image is valid, False otherwise
        """
        if image is None:
            logging.warning("Image is None")
            return False
        
        if not isinstance(image, Image.Image):
            logging.warning(f"Invalid image type: {type(image)}")
            return False
        
        if image.size == (0, 0) or image.width == 0 or image.height == 0:
            logging.warning(f"Image has zero dimensions: {image.size}")
            return False
        
        return True

    def _initialize_reader(self):
        """Initializes the EasyOCR reader in a separate thread to avoid blocking."""
        pass # Functionality removed intentionally

    def take_screenshot_region(self, region):
        """Takes a screenshot of the specified region (x, y, w, h)."""
        screenshot = pyautogui.screenshot(region=region)
        return screenshot

    def take_full_screenshot(self):
        """Takes a full screenshot of the primary monitor."""
        return pyautogui.screenshot()

    def perform_ocr(self, image):
        """Performs OCR on the given PIL image.
        
        Args:
            image: PIL Image object to process
            
        Returns:
            str: Extracted text or error message
        """
        return "OCR functionality is not available." # Functionality removed intentionally

class RegionSelector(tk.Toplevel):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.attributes('-alpha', 0.3)  # Transparency
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.config(cursor="cross")
        
        self.canvas = tk.Canvas(self, cursor="cross", bg="grey")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (event.x, event.y)
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x) # ERROR: Should be max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        width = x2 - x1
        height = y2 - y1
        
        if width > 5 and height > 5:
            self.withdraw()
            self.callback((x1, y1, width, height))
        
        self.destroy()