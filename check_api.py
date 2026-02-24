import requests
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"API Key: {GEMINI_API_KEY[:20]}...")
print(f"Valid format: {GEMINI_API_KEY.startswith('AIza')}")

# Test 1: List available models
print("\n--- Testing List Models ---")
response = requests.get(
    f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",
    timeout=30
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Available models:")
    for model in data.get('models', [])[:5]:
        name = model.get('name', 'unknown')
        print(f"  - {name}")
else:
    print(f"Error: {response.text[:200]}")

# Test 2: Try simple text request with gemini-1.5-flash
print("\n--- Testing gemini-1.5-flash (text only) ---")
payload = {
    "contents": [{
        "parts": [{"text": "Say hello"}]
    }]
}
headers = {"Content-Type": "application/json"}

response = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
    headers=headers,
    json=payload,
    timeout=30
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")

# Test 3: Try gemini-pro
print("\n--- Testing gemini-pro (text only) ---")
response = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
    headers=headers,
    json=payload,
    timeout=30
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")
