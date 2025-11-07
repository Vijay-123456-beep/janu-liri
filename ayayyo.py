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

        self.text_label = tk.Label(
            root,
            text="Press Hotkeys to Operate",
            font=("Helvetica", 12),
            bg="lightgray",
            wraplength=580
        )
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

        self.update_text("Processing with Gemini...")

        with open(self.last_capture_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this aptitude multiple-choice question and return only the correct answer and a short explanation."},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]
            }]
        }

        headers = {"Content-Type": "application/json"}

        for attempt in range(5):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 429:
                    wait = 2 ** attempt
                    self.update_text(f"Rate limit hit. Retrying in {wait} sec...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                answer_text = data['candidates'][0]['content']['parts'][0]['text']

                # ✅ Log usage
                self.log_usage()

                # ✅ Get stats
                today_count, month_count, last_90_count = self.get_usage_stats()

                # ✅ Estimated free quota
                MONTHLY_LIMIT = 1000
                remaining = MONTHLY_LIMIT - month_count
                percentage = max(0, (remaining / MONTHLY_LIMIT) * 100)

                if remaining < 50:
                    quota_message = f"⚠ LOW QUOTA: {remaining} req left ({percentage:.1f}% remaining)"
                else:
                    quota_message = f"✅ Remaining quota: {remaining} req ({percentage:.1f}%)"

                display = (
                    f"✅ Answer: {answer_text}\n\n"
                    f"📊 Usage Stats:\n"
                    f"➡ Today: {today_count}\n"
                    f"➡ This Month: {month_count}\n"
                    f"➡ Last 90 Days: {last_90_count}\n\n"
                    f"{quota_message}"
                )

                self.update_text(display)
                return

            except Exception as e:
                self.update_text(f"Error: {str(e)}")
                return

        self.update_text("Failed after multiple retries. Try again later.")

    def refresh(self):
        self.update_text("Overlay refreshed. Ready.")
        if self.last_capture_path and os.path.exists(self.last_capture_path):
            os.remove(self.last_capture_path)
            self.last_capture_path = None

    def update_text(self, message):
        self.text_label.config(text=message)


if __name__ == "__main__":
    root = tk.Tk()
    app = OverlayApp(root)
    root.mainloop()
