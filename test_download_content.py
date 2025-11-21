#!/usr/bin/env python3
"""Test the download_content method"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the completed video from earlier
job_id = "video_691a272a5a2481909f8a07bf7b6b5fcf03ce3fe0c2da10ab"

print(f"Downloading video {job_id}...")

try:
    content = client.videos.download_content(job_id)
    print(f"Content type: {type(content)}")
    print(f"Content dir: {[x for x in dir(content) if not x.startswith('_')]}")

    print(f"\nSaving to test_video_download.mp4...")
    with open('test_video_download.mp4', 'wb') as f:
        f.write(content.read())

    print(f"✓ Video downloaded successfully!")

    # Check file size
    size_mb = os.path.getsize('test_video_download.mp4') / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
