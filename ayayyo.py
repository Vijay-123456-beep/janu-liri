import tkinter as tk
import keyboard
import requests
import base64
import os
import time
from mss import mss
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- LOAD THE API KEY FROM .env ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SCREENSHOT_FILENAME = "capture.png"
USAGE_FILE = "usage_log.txt"

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

        # ✅ Scrollable Text Output
        self.text_area = tk.Text(root, font=("Helvetica", 11), wrap="word", bg="#e8e8e8")
        self.text_area.pack(side="left", fill="both", expand=True)

        self.scroll = tk.Scrollbar(root, command=self.text_area.yview)
        self.scroll.pack(side="right", fill="y")
        self.text_area.configure(yscrollcommand=self.scroll.set)

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
        was_visible = self.visible
        if was_visible:
            self.root.withdraw()

        with mss() as sct:
            sct.shot(mon=-1, output=SCREENSHOT_FILENAME)

        self.last_capture_path = SCREENSHOT_FILENAME
        self.update_text(f"Screenshot saved as {SCREENSHOT_FILENAME}")

        if was_visible:
            self.root.deiconify()

    def log_usage(self):
        """Logs each successful request with timestamp"""
        with open(USAGE_FILE, "a") as f:
            f.write(datetime.now().isoformat() + "\n")

    def get_usage_stats(self):
        """Reads usage_log.txt and counts usage"""
        if not os.path.exists(USAGE_FILE):
            return 0, 0, 0

        today = datetime.now().date()
        month_start = today.replace(day=1)
        days_90_ago = today - timedelta(days=90)

        today_count = 0
        month_count = 0
        last_90_count = 0

        with open(USAGE_FILE, "r") as f:
            for line in f:
                try:
                    timestamp = datetime.fromisoformat(line.strip()).date()
                    if timestamp == today:
                        today_count += 1
                    if timestamp >= month_start:
                        month_count += 1
                    if timestamp >= days_90_ago:
                        last_90_count += 1
                except:
                    pass

        return today_count, month_count, last_90_count

    def solve_capture(self):
        if not self.last_capture_path or not os.path.exists(self.last_capture_path):
            self.update_text("Error: Capture a screenshot first (Ctrl+Alt+C).")
            return

        if not GEMINI_API_KEY:
            self.update_text("Error: Missing API Key. Add it in .env file.")
            return

        self.update_text("Processing with Gemini...\n")

        with open(self.last_capture_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": (
                        "Read the question from the image. "
                        "If the question asks for a coding solution, detect the programming language automatically. "
                        "If it is a Java question, return ONLY the valid Java code. "
                        "If it is a Python question, return ONLY the valid Python code. "
                        "Do not include any explanation, comments, or extra text. "
                        "If it is an MCQ question, return ONLY the correct option letter (A/B/C/D) and its option text."
                    )},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]
            }]
        }

        headers = {"Content-Type": "application/json"}

        # ✅ Try up to 5 times if API temporarily fails
        for attempt in range(5):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                # Handle rate limits
                if response.status_code == 429:
                    wait = 2 ** attempt
                    self.update_text(f"Rate limit hit. Retrying in {wait} sec...\n")
                    time.sleep(wait)
                    continue

                # Handle server downtime (503)
                if response.status_code == 503:
                    wait = (attempt + 1) * 3
                    self.update_text(f"Server busy (503). Retrying in {wait} seconds...\n")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                answer_text = data['candidates'][0]['content']['parts'][0]['text']

                # ✅ Log success
                self.log_usage()
                today_count, month_count, last_90_count = self.get_usage_stats()

                display = (
                    f"{answer_text}\n\n"
                    f"--- API Usage ---\n"
                    f"Today: {today_count}\n"
                    f"Month: {month_count}\n"
                    f"90 Days: {last_90_count}\n"
                )

                self.update_text(display)
                return

            except Exception as e:
                self.update_text(f"Error: {str(e)}\nRetrying...\n")
                time.sleep(3)

        # ✅ Fallback to Flash model if Pro keeps failing
        try:
            self.update_text("Switching to backup model (gemini-1.5-flash)...\n")

            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            answer_text = data['candidates'][0]['content']['parts'][0]['text']

            self.log_usage()
            today_count, month_count, last_90_count = self.get_usage_stats()

            display = (
                f"{answer_text}\n\n"
                f"--- API Usage ---\n"
                f"Today: {today_count}\n"
                f"Month: {month_count}\n"
                f"90 Days: {last_90_count}\n"
                f"(⚡ Flash model was used as backup)"
            )
            self.update_text(display)

        except Exception as e:
            self.update_text("❌ Server unavailable. Please try again later.")
            return

    def refresh(self):
        self.update_text("Overlay refreshed. Ready.")
        if self.last_capture_path and os.path.exists(self.last_capture_path):
            os.remove(self.last_capture_path)
            self.last_capture_path = None

    def update_text(self, message):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, message)
        self.text_area.see(tk.END)  # auto scroll to bottom

if __name__ == "__main__":
    root = tk.Tk()
    app = OverlayApp(root)
    root.mainloop()
