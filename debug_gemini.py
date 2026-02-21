
import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
from fitting_system.ai_modules.gemini_client import GeminiClient
import google.generativeai as genai

print(f"Python executable: {sys.executable}")
print(f"Django settings configured.")
print(f"API Key from settings: {getattr(settings, 'GEMINI_API_KEY', 'NOT_FOUND')[:10]}...")

try:
    import google.generativeai
    print("google.generativeai imported successfully.")
    print(f"Version: {google.generativeai.__version__}")
except ImportError:
    print("ERROR: google.generativeai NOT installed.")

client = GeminiClient()
print(f"GeminiClient available: {client.available}")

if client.available:
    print("Attempting simple generation...")
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Hello, do you work?")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Generation failed: {e}")
else:
    print("Client not available, skipping generation test.")
