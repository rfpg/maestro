#!/usr/bin/env python3
"""Quick test to verify OpenAI API key is valid"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ Error: OPENAI_API_KEY not found in .env file")
    exit(1)

print(f"✓ API key found: {api_key[:20]}...{api_key[-4:]}")

# Test connection
try:
    client = OpenAI(api_key=api_key)

    # List available models (lightweight test)
    print("\n✓ Testing API connection...")
    models = client.models.list()

    print("✓ API connection successful!")
    print(f"\n✓ Your account has access to {len(list(models.data))} models")

    # Check for Sora models
    sora_models = [m for m in models.data if 'sora' in m.id.lower()]
    if sora_models:
        print(f"✓ Sora models available: {len(sora_models)}")
        for model in sora_models:
            print(f"  - {model.id}")
    else:
        print("\n⚠️  Note: Sora models not found in your model list.")
        print("   This might mean:")
        print("   - Sora access requires ChatGPT Pro subscription")
        print("   - API access may be different from ChatGPT Pro access")
        print("   - You may need to request Sora API access separately")

    print("\n✓ API key is valid and working!")

except Exception as e:
    print(f"❌ API connection failed: {e}")
    exit(1)
