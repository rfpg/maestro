#!/usr/bin/env python3
"""Test different methods to download a completed video"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the completed video from earlier
job_id = "video_691a272a5a2481909f8a07bf7b6b5fcf03ce3fe0c2da10ab"

print(f"Retrieving video {job_id}...")
video = client.videos.retrieve(job_id)

print(f"\nVideo status: {video.status}")
print(f"Video ID: {video.id}")

# Try different download methods
print("\n1. Checking if there's a download method...")
if hasattr(client.videos, 'download'):
    print("  Found videos.download method!")
else:
    print("  No videos.download method")

print("\n2. Checking if there's a content method...")
if hasattr(client.videos, 'content'):
    print("  Found videos.content method!")
    try:
        content = client.videos.content(video.id)
        print(f"  Content type: {type(content)}")
        print(f"  Saving to test_video.mp4...")
        with open('test_video.mp4', 'wb') as f:
            f.write(content.read())
        print(f"  ✓ Video downloaded successfully!")
    except Exception as e:
        print(f"  Error: {e}")
else:
    print("  No videos.content method")

print("\n3. Checking available methods on client.videos...")
for attr in dir(client.videos):
    if not attr.startswith('_') and callable(getattr(client.videos, attr)):
        print(f"  - {attr}")
