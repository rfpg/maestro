#!/usr/bin/env python3
"""
Sora Video Generator - Batch generate 1080p videos using OpenAI's Sora API
Optimized for ChatGPT Pro users to maximize video generation during subscription period
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    print("Error: OpenAI SDK not installed. Run: pip install openai>=1.51.0 python-dotenv>=1.0.0")
    exit(1)

# Load environment variables from .env file
load_dotenv()


class SoraVideoGenerator:
    """Generate videos using OpenAI's Sora API"""

    # Resolution presets (Sora 2 supported sizes)
    RESOLUTIONS = {
        "720p_landscape": (1280, 720),
        "720p_portrait": (720, 1280),
        "1024p_landscape": (1792, 1024),
        "1024p_portrait": (1024, 1792),
    }

    # Model options
    MODELS = {
        "standard": "sora-2",      # 70-80% cost savings
        "pro": "sora-2-pro"         # Higher quality
    }

    def __init__(self, api_key: Optional[str] = None, output_dir: str = "generated_videos"):
        """
        Initialize the Sora Video Generator

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env variable)
            output_dir: Directory to save generated videos
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env variable or pass api_key parameter")

        self.client = OpenAI(api_key=self.api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Stats tracking
        self.stats = {
            "total_requested": 0,
            "completed": 0,
            "failed": 0,
            "total_cost_estimate": 0.0,
            "total_seconds_generated": 0
        }

    def generate_video(
        self,
        prompt: str,
        duration: int = 10,
        resolution: str = "1080p_landscape",
        model: str = "standard",
        max_retries: int = 3,
        poll_interval: int = 10
    ) -> Optional[Dict]:
        """
        Generate a single video

        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds (max depends on model)
            resolution: Resolution preset key from RESOLUTIONS
            model: Model to use ('standard' or 'pro')
            max_retries: Number of retry attempts on failure
            poll_interval: Seconds between status checks

        Returns:
            Dictionary with video info and file path, or None if failed
        """
        if resolution not in self.RESOLUTIONS:
            raise ValueError(f"Invalid resolution. Choose from: {list(self.RESOLUTIONS.keys())}")

        if model not in self.MODELS:
            raise ValueError(f"Invalid model. Choose from: {list(self.MODELS.keys())}")

        width, height = self.RESOLUTIONS[resolution]
        model_name = self.MODELS[model]

        # Cost estimation ($0.1-$0.3 per second, using mid-range)
        cost_per_second = 0.1 if model == "standard" else 0.3
        estimated_cost = duration * cost_per_second

        print(f"\n{'='*80}")
        print(f"Generating video:")
        print(f"  Prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
        print(f"  Duration: {duration}s")
        print(f"  Resolution: {resolution} ({width}x{height})")
        print(f"  Model: {model_name}")
        print(f"  Estimated cost: ${estimated_cost:.2f}")
        print(f"{'='*80}")

        self.stats["total_requested"] += 1

        for attempt in range(max_retries):
            try:
                # Create video generation job
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Creating video generation job...")

                response = self.client.videos.create(
                    model=model_name,
                    prompt=prompt,
                    size=f"{width}x{height}",
                    seconds=str(duration)
                )

                job_id = response.id
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Job created: {job_id}")

                # Poll for completion
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for generation to complete...")
                print(f"  (This typically takes 80-90 seconds for a {duration}-second video)")

                start_time = time.time()
                while True:
                    status_response = self.client.videos.retrieve(job_id)
                    status = status_response.status

                    elapsed = int(time.time() - start_time)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status} (elapsed: {elapsed}s)", end='\r')

                    if status in ["succeeded", "completed"]:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Video generation succeeded!")

                        # Download the video
                        filename = self._generate_filename(prompt, resolution, duration)
                        filepath = self.output_dir / filename

                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Downloading video to {filepath}...")
                        video_data = self.client.videos.download_content(job_id)

                        with open(filepath, 'wb') as f:
                            f.write(video_data.read())

                        # Update stats
                        self.stats["completed"] += 1
                        self.stats["total_cost_estimate"] += estimated_cost
                        self.stats["total_seconds_generated"] += duration

                        result = {
                            "job_id": job_id,
                            "prompt": prompt,
                            "filepath": str(filepath),
                            "resolution": resolution,
                            "duration": duration,
                            "model": model_name,
                            "cost_estimate": estimated_cost,
                            "generation_time": elapsed
                        }

                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Video saved successfully!")
                        return result

                    elif status in ["failed", "cancelled"]:
                        error_msg = getattr(status_response, 'error', 'Unknown error')
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Generation {status}: {error_msg}")
                        break

                    # Still processing
                    time.sleep(poll_interval)

            except Exception as e:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.stats["failed"] += 1
                    return None

        self.stats["failed"] += 1
        return None

    def batch_generate(
        self,
        prompts: List[str],
        duration: int = 10,
        resolution: str = "1080p_landscape",
        model: str = "standard",
        delay_between_jobs: int = 2
    ) -> List[Dict]:
        """
        Generate multiple videos from a list of prompts

        Args:
            prompts: List of text prompts
            duration: Video duration in seconds
            resolution: Resolution preset
            model: Model to use
            delay_between_jobs: Seconds to wait between job submissions

        Returns:
            List of result dictionaries for successful generations
        """
        results = []
        total = len(prompts)

        print(f"\n{'='*80}")
        print(f"BATCH VIDEO GENERATION")
        print(f"{'='*80}")
        print(f"Total prompts: {total}")
        print(f"Duration per video: {duration}s")
        print(f"Resolution: {resolution}")
        print(f"Model: {model}")
        print(f"{'='*80}\n")

        for i, prompt in enumerate(prompts, 1):
            print(f"\n>>> Processing {i}/{total}")

            result = self.generate_video(
                prompt=prompt,
                duration=duration,
                resolution=resolution,
                model=model
            )

            if result:
                results.append(result)

            # Delay between jobs to avoid rate limits
            if i < total:
                print(f"\nWaiting {delay_between_jobs}s before next job...")
                time.sleep(delay_between_jobs)

        return results

    def _generate_filename(self, prompt: str, resolution: str, duration: int) -> str:
        """Generate a safe filename from prompt"""
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create safe prompt snippet (first 40 chars, alphanumeric only)
        safe_prompt = "".join(c if c.isalnum() or c.isspace() else '' for c in prompt)
        safe_prompt = "_".join(safe_prompt.split())[:40]

        return f"{timestamp}_{safe_prompt}_{resolution}_{duration}s.mp4"

    def print_stats(self):
        """Print generation statistics"""
        print(f"\n{'='*80}")
        print("GENERATION STATISTICS")
        print(f"{'='*80}")
        print(f"Total requested:       {self.stats['total_requested']}")
        print(f"Completed:             {self.stats['completed']}")
        print(f"Failed:                {self.stats['failed']}")
        print(f"Total video seconds:   {self.stats['total_seconds_generated']}s")
        print(f"Estimated total cost:  ${self.stats['total_cost_estimate']:.2f}")
        print(f"Output directory:      {self.output_dir.absolute()}")
        print(f"{'='*80}\n")

    def save_results_log(self, results: List[Dict], filename: str = "generation_log.json"):
        """Save generation results to a JSON log file"""
        log_path = self.output_dir / filename

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "results": results
        }

        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"Results log saved to: {log_path}")


def load_prompts_from_file(filepath: str) -> List[str]:
    """Load prompts from a text file (one prompt per line)"""
    with open(filepath, 'r') as f:
        prompts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return prompts


def main():
    parser = argparse.ArgumentParser(description="Generate videos using OpenAI Sora API")
    parser.add_argument('--prompt', type=str, help='Single prompt for video generation')
    parser.add_argument('--prompts-file', type=str, help='File containing prompts (one per line)')
    parser.add_argument('--duration', type=int, default=12, choices=[4, 8, 12],
                       help='Video duration in seconds: 4, 8, or 12 (default: 12)')
    parser.add_argument('--resolution', type=str, default='720p_landscape',
                       choices=['720p_landscape', '720p_portrait', '1024p_landscape', '1024p_portrait'],
                       help='Video resolution (default: 720p_landscape)')
    parser.add_argument('--model', type=str, default='standard', choices=['standard', 'pro'],
                       help='Model to use: standard (sora-2) or pro (sora-2-pro, default: standard)')
    parser.add_argument('--output-dir', type=str, default='generated_videos',
                       help='Output directory for videos (default: generated_videos)')
    parser.add_argument('--api-key', type=str, help='OpenAI API key (or set OPENAI_API_KEY env var)')

    args = parser.parse_args()

    # Validate inputs
    if not args.prompt and not args.prompts_file:
        parser.error("Either --prompt or --prompts-file must be provided")

    # Initialize generator
    try:
        generator = SoraVideoGenerator(api_key=args.api_key, output_dir=args.output_dir)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Generate videos
    results = []

    if args.prompt:
        # Single video generation
        result = generator.generate_video(
            prompt=args.prompt,
            duration=args.duration,
            resolution=args.resolution,
            model=args.model
        )
        if result:
            results.append(result)

    elif args.prompts_file:
        # Batch generation
        try:
            prompts = load_prompts_from_file(args.prompts_file)
            print(f"Loaded {len(prompts)} prompts from {args.prompts_file}")

            results = generator.batch_generate(
                prompts=prompts,
                duration=args.duration,
                resolution=args.resolution,
                model=args.model
            )
        except FileNotFoundError:
            print(f"Error: File not found: {args.prompts_file}")
            return

    # Print final statistics
    generator.print_stats()

    # Save results log
    if results:
        generator.save_results_log(results)


if __name__ == "__main__":
    main()
