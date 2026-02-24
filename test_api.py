import requests
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# List available models
print("Fetching available Gemini models...")
response = requests.get(
    f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
)

if response.status_code == 200:
    data = response.json()
    print("\nAvailable models:")
    for model in data.get('models', []):
        print(f"  - {model['name']}")
        if 'supportedGenerationMethods' in model:
            print(f"    Methods: {model['supportedGenerationMethods']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
