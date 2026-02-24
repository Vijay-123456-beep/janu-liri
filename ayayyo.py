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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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

        if not OPENROUTER_API_KEY:
            self.update_text("❌ Error: Missing OPENROUTER_API_KEY in .env file.\n\nGet a free key from: https://openrouter.ai/keys")
            return

        self.update_text("Processing with OpenRouter...\n")

        # Check screenshot file
        try:
            file_size = os.path.getsize(self.last_capture_path)
            self.update_text(f"Screenshot size: {file_size} bytes\n")
            
            if file_size == 0:
                self.update_text("Error: Screenshot file is empty!\n")
                return
            
            if file_size > 20 * 1024 * 1024:  # 20MB limit
                self.update_text("Error: Screenshot too large (>20MB)\n")
                return
        except Exception as e:
            self.update_text(f"Error checking screenshot: {str(e)}\n")
            return

        with open(self.last_capture_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        self.update_text(f"Image data encoded: {len(image_data)} chars\n")

        payload = {
            "model": "nvidia/nemotron-nano-12b-v2-vl:free",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image and answer the question shown. Provide a concise answer."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }]
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://openrouter.ai",
            "X-Title": "MCQ Solver App"
        }
        
        for attempt in range(3):
            try:
                self.update_text(f"OpenRouter: Attempt {attempt + 1}...\n")
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )

                # Log to file for debugging
                with open("debug.log", "a") as f:
                    f.write(f"\n--- Attempt {attempt + 1} ---\n")
                    f.write(f"Status: {response.status_code}\n")
                    f.write(f"Response: {response.text[:1000]}\n")

                # Always check response content first
                try:
                    data = response.json()
                except:
                    msg = f"Invalid JSON response\nResponse: {response.text[:200]}\n"
                    self.update_text(msg)
                    with open("debug.log", "a") as f:
                        f.write(f"JSON Parse Error: {response.text}\n")
                    continue

                # Log full response for debugging
                if response.status_code != 200:
                    if 'error' in data:
                        error_msg = data['error'].get('message', str(data['error']))
                        msg = f"OpenRouter - HTTP {response.status_code}\nError: {error_msg}\n"
                    else:
                        msg = f"OpenRouter - HTTP {response.status_code}\nResponse: {response.text[:300]}\n"
                    self.update_text(msg)
                    
                    # Retry on 429/503
                    if response.status_code in [429, 503]:
                        wait = 2 ** attempt
                        self.update_text(f"Retrying in {wait} seconds...\n")
                        time.sleep(wait)
                        continue
                    break

                # Check for API errors in response
                if 'error' in data:
                    error_msg = data['error'].get('message', str(data['error']))
                    self.update_text(f"API Error: {error_msg}\nRetrying...\n")
                    time.sleep(2)
                    continue
                
                if 'choices' not in data or not data['choices']:
                    self.update_text(f"No response from API.\n")
                    with open("debug.log", "a") as f:
                        f.write(f"No choices. Data: {str(data)[:500]}\n")
                    continue
                
                # Check if choice has content
                choice = data['choices'][0]
                if 'message' not in choice or 'content' not in choice['message']:
                    self.update_text(f"Invalid response structure\n")
                    with open("debug.log", "a") as f:
                        f.write(f"Invalid structure. Choice: {str(choice)[:500]}\n")
                    continue
                    
                answer_text = choice['message']['content']

                # ✅ Log success
                self.log_usage()
                today_count, month_count, last_90_count = self.get_usage_stats()

                display = (
                    f"{answer_text}\n\n"
                    f"--- API Usage ---\n"
                    f"Today: {today_count}\n"
                    f"Month: {month_count}\n"
                    f"90 Days: {last_90_count}\n"
                    f"(OpenRouter)"
                )

                self.update_text(display)
                return

            except requests.exceptions.Timeout:
                self.update_text(f"⏱️ Timeout. Retrying...\n")
                time.sleep(5)
            except requests.exceptions.ConnectionError as ce:
                self.update_text(f"🌐 Connection error\nRetrying...\n")
                time.sleep(5)
            except Exception as e:
                msg = f"❌ {type(e).__name__}: {str(e)[:80]}\n"
                self.update_text(msg)
                with open("debug.log", "a") as f:
                    f.write(f"Exception: {type(e).__name__}: {str(e)}\n")
                time.sleep(3)

        # ✅ All attempts exhausted
        msg = "❌ OpenRouter failed.\n\n📋 Check debug.log for details\n\nPossible causes:\n- Invalid API key\n- No credits\n- Server issue\n\nTry: https://openrouter.ai/account/usage"
        self.update_text(msg)
        with open("debug.log", "a") as f:
            f.write(f"\n=== ALL ATTEMPTS FAILED ===\n")

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
