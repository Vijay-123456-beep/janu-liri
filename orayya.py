import tkinter as tk
import keyboard
import requests
import base64
import os
from mss import mss

# --- CONFIGURATION ---
# IMPORTANT: Revoke the key you shared and replace this with a new one.
GEMINI_API_KEY = "AIzaSyCswmzZY_Vjyo8UNNRBOg-x9y3pNZCPBbI"
SCREENSHOT_FILENAME = "capture.png"

# --- HOTKEYS ---
TOGGLE_HOTKEY = "ctrl+alt+t"
CAPTURE_HOTKEY = "ctrl+alt+c"
SOLVE_HOTKEY = "ctrl+alt+s"
REFRESH_HOTKEY = "ctrl+alt+r"

class OverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.geometry("600x400+100+100")
        self.root.lift()
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "white")
        self.root.config(bg='white')

        self.text_label = tk.Label(root, text="Press Hotkeys to Operate", font=("Helvetica", 12), bg="lightgray", wraplength=580)
        self.text_label.pack(expand=True, fill="both")

        self.visible = True
        self.last_capture_path = None
        self.setup_hotkeys()
        
    def setup_hotkeys(self):
        keyboard.add_hotkey(TOGGLE_HOTKEY, self.toggle_visibility)
        keyboard.add_hotkey(CAPTURE_HOTKEY, self.capture_screen)
        keyboard.add_hotkey(SOLVE_HOTKEY, self.solve_capture)
        keyboard.add_hotkey(REFRESH_HOTKEY, self.refresh)

    def toggle_visibility(self):
        if self.visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
        self.visible = not self.visible

    def capture_screen(self):
        is_currently_visible = self.visible
        if is_currently_visible:
            self.root.withdraw()

        with mss() as sct:
            sct.shot(mon=-1, output=SCREENSHOT_FILENAME)
        self.last_capture_path = SCREENSHOT_FILENAME
        self.update_text(f"Screenshot saved as {SCREENSHOT_FILENAME}")
        # Restore previous visibility state
        if is_currently_visible:
            # If it was visible before capture, show it again
            self.root.deiconify()

    def solve_capture(self):
        if not self.last_capture_path or not os.path.exists(self.last_capture_path):
            self.update_text("Error: Capture a screenshot first (Ctrl+Alt+C).")
            return

        # --- FIX #1: Corrected the API Key check ---
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_NEW_GEMINI_API_KEY":
            self.update_text("Error: Set your new Gemini API Key in the script.")
            return

        self.update_text("Processing with Gemini...")
        
        with open(self.last_capture_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this image of a multiple-choice question. Identify the question and the options, then determine the correct answer. Provide only the letter of the correct option and a brief, one-sentence explanation."},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]
            }]
        }
        
        try:
            # --- FIX #2: Corrected the model endpoint URL ---
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            answer = result['candidates'][0]['content']['parts'][0]['text']
            self.update_text(f"Answer: {answer}")
        except Exception as e:
            self.update_text(f"API Error: {str(e)}")


    def refresh(self):
        self.update_text("Overlay refreshed. Ready for commands.")
        if self.last_capture_path and os.path.exists(self.last_capture_path):
            os.remove(self.last_capture_path)
            self.last_capture_path = None

    def update_text(self, message):
        self.text_label.config(text=message)

if __name__ == "__main__":
    root = tk.Tk()
    app = OverlayApp(root)
    root.mainloop()