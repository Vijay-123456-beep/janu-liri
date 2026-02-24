import tkinter as tk
import keyboard
import requests
import base64
import os
from mss import mss
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load API key from .env file
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "nvidia/nemotron-nano-12b-v2-vl:free"
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
        
        if not is_currently_visible:
            self.root.deiconify()
            self.root.withdraw()

    def solve_capture(self):
        if not self.last_capture_path or not os.path.exists(self.last_capture_path):
            self.update_text("Error: Capture a screenshot first (Ctrl+Alt+C).")
            return

        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
            self.update_text("Error: Set your OpenRouter API Key in the script.")
            return

        self.update_text("Processing with OpenRouter...")
        
        with open(self.last_capture_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://openrouter.ai",
            "X-Title": "MCQ Solver App"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image of a multiple-choice question. Identify the question and the options, then determine the correct answer. Provide only the letter of the correct option and a brief, one-sentence explanation."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }]
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            # Check if the response contains an error
            if 'error' in result:
                self.update_text(f"API Error: {result['error'].get('message', str(result['error']))}")
                return
            
            if 'choices' not in result or not result['choices']:
                self.update_text(f"Unexpected response format: {str(result)[:200]}")
                return
                
            answer = result['choices'][0]['message']['content']
            self.update_text(f"Answer: {answer}")
        except requests.exceptions.Timeout:
            self.update_text("Error: Request timed out. The API is taking too long. Try again.")
        except requests.exceptions.ConnectionError as e:
            self.update_text(f"Error: Network connection failed. Check your internet and try again.")
        except requests.exceptions.HTTPError as e:
            self.update_text(f"HTTP Error {response.status_code}: {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            self.update_text(f"Network Error: {str(e)}")
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