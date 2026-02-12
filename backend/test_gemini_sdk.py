"""
Test which Gemini SDK is installed and what models are available
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

print("=" * 60)
print("Gemini SDK Diagnostic Tool")
print("=" * 60)

# Check which SDK is installed
print("\n1️⃣ Checking installed packages...")
import subprocess
result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
lines = result.stdout.split('\n')
for line in lines:
    if 'google' in line.lower() and ('genai' in line.lower() or 'generative' in line.lower()):
        print(f"   {line}")

# Try to import new SDK
print("\n2️⃣ Testing new SDK import...")
try:
    from google import genai
    print("   ✅ Successfully imported: from google import genai")
    
    # Try to create client
    print("\n3️⃣ Creating Gemini client...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("   ✅ Client created successfully")
    
    # List available models
    print("\n4️⃣ Listing available models...")
    try:
        models = client.models.list()
        print("   Available models:")
        for model in models:
            # Check if it supports generate_content
            print(f"   • {model.name}")
        
        print("\n✅ SDK is working! Use one of the models above.")
        
    except Exception as e:
        print(f"   ❌ Error listing models: {e}")
        
except ImportError as e:
    print(f"   ❌ Cannot import new SDK: {e}")
    print("\n   Install it with: pip install google-genai")
    
    # Try old SDK
    print("\n   Trying old SDK...")
    try:
        import google.generativeai as genai_old
        print("   ⚠️  Old SDK found: google.generativeai")
        print("   This uses v1beta endpoint!")
        print("\n   FIX: Run these commands:")
        print("   pip uninstall google-generativeai google-ai-generativelanguage -y")
        print("   pip install google-genai")
    except:
        print("   No SDK found at all!")

print("\n" + "=" * 60)
