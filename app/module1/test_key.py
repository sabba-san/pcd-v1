import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GROQ_API_KEY")

if key:
    print("✅ API Key loaded successfully!")
    # print(f"Key starts with: {key[:4]}...") # Optional: verify content
else:
    print("❌ API Key NOT found!")
