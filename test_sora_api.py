#!/usr/bin/env python3
"""Test Sora API to see what parameters it actually accepts"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test what parameters the API actually accepts
print("Testing Sora API parameters...")
print("\nAttempting simple video generation...")

try:
    # Try minimal parameters
    response = client.videos.generate(
        model="sora-2",
        prompt="A serene mountain landscape at sunset"
    )
    print(f"Success! Response: {response}")
except AttributeError as e:
    print(f"AttributeError: {e}")
    print("\nTrying alternative method...")

    # Check what methods are available
    print(f"\nAvailable methods on client.videos: {dir(client.videos)}")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    print("\nThis suggests the Sora API might not be available yet or requires different access.")
    print("The API might still be in beta or require special access beyond ChatGPT Pro.")
