#!/usr/bin/env python3
"""
Process Byron's Darkness poem - split by semicolons and create prompts file
"""

# Read the poem
with open('darkness_poem.txt', 'r') as f:
    poem = f.read()

# Split by semicolons and clean up each segment
segments = [seg.strip().replace('\n', ' ').replace('  ', ' ')
            for seg in poem.split(';') if seg.strip()]

# Create prompts file
with open('darkness_prompts.txt', 'w') as f:
    for i, segment in enumerate(segments, 1):
        # Add context for better video generation
        f.write(f"{segment}\n")

print(f"Created {len(segments)} video prompts from the poem")
print(f"\nPrompts saved to: darkness_prompts.txt")
print(f"\nFirst 3 prompts:")
for i, seg in enumerate(segments[:3], 1):
    print(f"\n{i}. {seg[:100]}...")

print(f"\n\nEstimated cost:")
print(f"  {len(segments)} videos × 12 seconds × $0.10/second = ${len(segments) * 12 * 0.10:.2f}")
print(f"\nTotal video time: {len(segments) * 12} seconds ({len(segments) * 12 / 60:.1f} minutes)")
