# Maestro 🎻

An agentic media studio that conducts video and audio into one production.

**Two acts:**
- **🎬 Video generation** — batch-generate 1080p clips with OpenAI's Sora API. (`sora_video_generator.py`)
- **🎙️ AI commentary** — watch footage and lay on broadcast-style play-by-play: an energetic British lead commentator, a daft cockney co-commentator, and a reactive Premier-League crowd with goal roars — all auto-mixed onto your video. (`video_commentator.py`)

(Jump to the **🎙️ AI commentary** section below for the second act.)

---

## 🎬 Video generation (Sora)

A Python tool to batch-generate 1080p videos using OpenAI's Sora API, optimized for ChatGPT Pro subscribers.

### Features

- Generate high-quality 1080p videos in multiple aspect ratios
- Batch processing from text file of prompts
- Support for both Sora-2 (standard) and Sora-2 Pro models
- Automatic retry logic and error handling
- Cost estimation and tracking
- Progress monitoring with detailed statistics
- Organized output with timestamped filenames

## Requirements

- Python 3.8+
- OpenAI API key (ChatGPT Pro subscription)
- Internet connection

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file

   OR set as environment variable:
   ```bash
   export OPENAI_API_KEY='sk-your-api-key-here'
   ```

## Usage

### Generate a Single Video

```bash
python sora_video_generator.py \
  --prompt "A golden retriever playing in a field of sunflowers" \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard
```

### Batch Generate from File

1. Create a text file with prompts (one per line):
```bash
# prompts.txt
A sunset over the ocean
A cat playing piano
City lights at night
```

2. Run batch generation:
```bash
python sora_video_generator.py \
  --prompts-file prompts.txt \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard
```

### Quick Start with Example Prompts

```bash
python sora_video_generator.py \
  --prompts-file example_prompts.txt \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard
```

## Command-Line Arguments

| Argument | Description | Default | Options |
|----------|-------------|---------|---------|
| `--prompt` | Single prompt for video generation | None | Any text |
| `--prompts-file` | File with prompts (one per line) | None | File path |
| `--duration` | Video duration in seconds | 10 | Integer |
| `--resolution` | Video resolution | 1080p_landscape | 1080p_square, 1080p_portrait, 1080p_landscape |
| `--model` | Sora model to use | standard | standard (sora-2), pro (sora-2-pro) |
| `--output-dir` | Directory for generated videos | generated_videos | Any path |
| `--api-key` | OpenAI API key | Env variable | Your API key |

## Resolution Options

- **1080p_square**: 1080x1080 (Instagram, social media)
- **1080p_portrait**: 1080x1920 (TikTok, Instagram Stories/Reels)
- **1080p_landscape**: 1920x1080 (YouTube, standard video)

## Model Comparison

### Standard (sora-2)
- 70-80% cost savings vs Pro
- Estimated cost: ~$0.10 per second
- Good quality for most use cases
- **Recommended for maximizing video count**

### Pro (sora-2-pro)
- Higher quality and realism
- Estimated cost: ~$0.30 per second
- Better physics and instruction-following
- Best for premium content

## Cost Estimation

For a 10-second video:
- **Standard model**: ~$1.00 per video
- **Pro model**: ~$3.00 per video

With ChatGPT Pro for one month:
- **Standard model**: Generate ~1000 videos for ~$1000
- **Pro model**: Generate ~330 videos for ~$1000

*(Actual costs may vary based on OpenAI's pricing)*

## Output

Generated videos are saved to the output directory with filenames in this format:
```
YYYYMMDD_HHMMSS_prompt_snippet_resolution_duration.mp4
```

Example:
```
20250115_143052_golden_retriever_playing_in_field_1080p_landscape_10s.mp4
```

A JSON log file (`generation_log.json`) is also created with:
- Generation statistics
- Cost estimates
- File paths
- Timestamps

## Tips for Maximum Output

1. **Use the standard model** - 3x more videos for the same cost
2. **Batch process** - Create a large prompts file and let it run
3. **Optimize prompts** - Clear, concise prompts work best
4. **Monitor rate limits** - The script includes delays to avoid hitting API limits
5. **Check your API usage** - Monitor at platform.openai.com
6. **Start with shorter durations** - Test with 5s videos before committing to 10s

## Example Workflow

```bash
# 1. Create your prompts file
cat > my_prompts.txt << EOF
Sunset over mountains
Ocean waves at beach
City skyline at night
Forest with morning fog
EOF

# 2. Generate all videos
python sora_video_generator.py \
  --prompts-file my_prompts.txt \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard \
  --output-dir my_videos

# 3. Check the results
ls -lh my_videos/
cat my_videos/generation_log.json
```

## Troubleshooting

**Error: OpenAI SDK not installed**
```bash
pip install openai>=1.51.0
```

**Error: API key required**
- Set the `OPENAI_API_KEY` environment variable
- Or pass `--api-key` argument
- Or create a `.env` file with your key

**Rate limit errors**
- Increase delay between jobs with a longer `delay_between_jobs` value in the code
- Wait a few minutes between batch runs
- Check your API usage limits

**Generation failures**
- Check your API key has access to Sora
- Verify you have ChatGPT Pro subscription
- Check prompt doesn't violate content policies
- Review error messages in console output

## API Access Notes

- Sora API is currently in preview for OpenAI developers
- ChatGPT Pro subscription required
- Check platform.openai.com for current API access status
- API availability may be region-specific

---

## 🎙️ AI commentary (`video_commentator.py`)

Turn raw match footage into a fully commentated highlight reel — an excitable British lead commentator, a daft working-class cockney co-commentator who chimes in during the gaps, and a reactive Premier-League crowd, all mixed onto the video.

```bash
# Guide-driven: build the commentary from a spoken guide recording (most accurate timing/names)
python video_commentator.py --video match.mov --guide-audio guide.m4a --keep-original-audio

# Script-driven: pin every line to exact timestamps from an events file
python video_commentator.py --video match.mov --events events.json --keep-original-audio

# Vision baseline: let a model watch the frames and commentate (no guide needed)
python video_commentator.py --video match.mov --keep-original-audio
```

Highlights:
- **Lead voice** (ElevenLabs) with emotion scaled per moment; **goals shout, misses groan.**
- **Cockney co-commentator** (ElevenLabs) dropping useless one-liners, one at a time, only in the lead's silent gaps.
- **Reactive crowd**: a chanting stadium bed, anticipation swells on crosses/shots, roars on goals, groans on misses.
- **Exact timing**: goals/misses pinned to timestamps; the engine auto-prevents overlapping voices.
- Needs `OPENAI_API_KEY` (vision/transcription) and `ELEVENLABS_API_KEY` (voices + crowd) in `.env`.

## License

A utility suite for personal use with OpenAI's Sora & ElevenLabs APIs. Ensure you comply with each provider's terms of service and usage policies.
