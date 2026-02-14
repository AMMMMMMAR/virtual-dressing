
import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    import google.generativeai as genai
    print("google.generativeai imported successfully.")
except ImportError:
    print("Error: google-generativeai package not installed.")
    sys.exit(1)

api_key = getattr(settings, 'GEMINI_API_KEY', None)
print(f"API Key configured: {'Yes' if api_key else 'No'}")

if not api_key:
    print("Error: No API key found in settings.")
    sys.exit(1)

print(f"API Key (first 5 chars): {api_key[:5]}...")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("Model initialized.")
    
    print("Attempting to generate content...")
    response = model.generate_content("Hello, can you hear me?")
    print("Response received:")
    print(response.text)
    print("SUCCESS: Gemini API is working.")
    
except Exception as e:
    print(f"FAILURE: Gemini API call failed.")
    print(f"Error details: {e}")
