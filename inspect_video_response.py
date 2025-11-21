#!/usr/bin/env python3
"""Inspect the Video response object to see what attributes it has"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the completed video from earlier
job_id = "video_691a272a5a2481909f8a07bf7b6b5fcf03ce3fe0c2da10ab"

print(f"Retrieving video {job_id}...")
response = client.videos.retrieve(job_id)

print(f"\nResponse type: {type(response)}")
print(f"\nResponse object: {response}")
print(f"\nDir of response:")
for attr in dir(response):
    if not attr.startswith('_'):
        print(f"  {attr}: {getattr(response, attr, 'N/A')}")
