# Getting Started with Sora Video Generator

This guide will help you start generating videos with OpenAI's Sora API using your ChatGPT Pro subscription.

## Prerequisites

1. **ChatGPT Pro subscription** (active)
2. **OpenAI API key** with Sora access
3. **Python 3.8+** installed on your system
4. **Budget** allocated for API usage

## Quick Setup (5 Minutes)

### 1. Install Dependencies

Run the quick start script:
```bash
./quick_start.sh
```

Or manually:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure API Key

Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Where to get your API key:**
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Copy and paste it into your `.env` file

### 3. Plan Your Strategy

Use the subscription planner to calculate your optimal approach:

```bash
# Default: $1000 budget, 30 days, standard model
python subscription_planner.py

# Custom parameters
python subscription_planner.py --budget 500 --days 20 --duration 10 --model standard

# Compare models
python subscription_planner.py --compare

# See weekly schedule
python subscription_planner.py --schedule
```

Example output:
```
CHATGPT PRO SUBSCRIPTION - VIDEO GENERATION PLAN
================================================================================

Subscription Details:
  Days remaining:        30 days
  Total budget:          $1,000.00
  Daily budget:          $33.33/day

Video Configuration:
  Model:                 standard (sora-2)
  Duration per video:    10 seconds
  Cost per video:        $1.00

Maximum Output:
  Total videos:          1,000 videos
  Videos per day:        33.3 videos/day
  Total video content:   2.8 hours (167 minutes)
```

## Usage Examples

### Example 1: Single Video Test

Start with a test video to verify everything works:

```bash
python sora_video_generator.py \
  --prompt "A golden retriever playing in a field of sunflowers at sunset" \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard
```

This will:
- Generate one 10-second video
- Save it to `generated_videos/`
- Show progress and cost estimate
- Take ~80-90 seconds to complete

### Example 2: Batch Generate from File

Create a file with your prompts (`my_prompts.txt`):
```
A sunset over the ocean with gentle waves
A cozy coffee shop interior with morning light
City skyline at night with twinkling lights
Forest path with morning fog
```

Generate all videos:
```bash
python sora_video_generator.py \
  --prompts-file my_prompts.txt \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard
```

### Example 3: Use Provided Examples

We included 15 example prompts to get you started:

```bash
python sora_video_generator.py \
  --prompts-file example_prompts.txt \
  --duration 10 \
  --resolution 1080p_portrait \
  --model standard
```

### Example 4: Different Resolutions

Generate for different platforms:

```bash
# YouTube (landscape)
python sora_video_generator.py \
  --prompts-file youtube_prompts.txt \
  --resolution 1080p_landscape

# Instagram/TikTok (portrait)
python sora_video_generator.py \
  --prompts-file social_prompts.txt \
  --resolution 1080p_portrait

# Instagram posts (square)
python sora_video_generator.py \
  --prompts-file instagram_prompts.txt \
  --resolution 1080p_square
```

## Best Practices

### 1. Start Small
- Generate 1-2 test videos first
- Verify quality meets your needs
- Confirm API access is working

### 2. Create Good Prompts
```
✓ GOOD: "A golden retriever puppy playing with a red ball in a sunny park"
✗ BAD: "dog"

✓ GOOD: "Slow motion ocean waves crashing on a rocky beach at sunset"
✗ BAD: "beach scene"

✓ GOOD: "Aerial view of a winding river through autumn forest with colorful foliage"
✗ BAD: "forest river"
```

**Prompt Tips:**
- Be specific and descriptive
- Include details about: subject, action, setting, lighting, style
- Mention camera angles if important
- Keep prompts under 200 characters for best results

### 3. Organize Your Prompts

Create themed prompt files:
```
prompts/
├── nature_scenes.txt
├── urban_scenes.txt
├── abstract.txt
└── product_shots.txt
```

### 4. Monitor Costs

Check your spending regularly:
```bash
# View stats from last run
cat generated_videos/generation_log.json

# Check OpenAI dashboard
# https://platform.openai.com/usage
```

### 5. Batch Processing Strategy

For maximum efficiency:

```bash
# Create a daily prompt file with 30-50 prompts
cat > daily_batch_1.txt << EOF
Prompt 1
Prompt 2
...
Prompt 50
EOF

# Run overnight or during downtime
nohup python sora_video_generator.py \
  --prompts-file daily_batch_1.txt \
  --duration 10 \
  --resolution 1080p_landscape \
  --model standard > output.log 2>&1 &

# Check progress
tail -f output.log
```

## Maximizing Your Subscription

### Cost Optimization

| Strategy | Videos/Month | Cost | Best For |
|----------|--------------|------|----------|
| Standard, 10s | ~1000 | ~$1000 | Maximum quantity |
| Standard, 5s | ~2000 | ~$1000 | Shorter clips |
| Pro, 10s | ~330 | ~$1000 | Premium quality |
| Mixed (70% std, 30% pro) | ~760 | ~$1000 | Balanced approach |

### Time Management

Generation time per video: ~85 seconds
- 100 videos = ~2.4 hours
- 500 videos = ~12 hours
- 1000 videos = ~24 hours (continuous)

**Tip:** Run batch jobs overnight or during work hours

### Quality vs Quantity

**Choose Standard (sora-2) if:**
- You need high volume
- Content is for social media
- Budget is limited
- Testing/prototyping

**Choose Pro (sora-2-pro) if:**
- Premium content needed
- Client projects
- Final production
- Complex physics/motion

## Troubleshooting

### Issue: "OpenAI API key required"
**Solution:**
```bash
# Check .env file exists
cat .env

# Verify key is set
echo $OPENAI_API_KEY

# Or pass directly
python sora_video_generator.py --api-key sk-your-key-here --prompt "test"
```

### Issue: "Rate limit exceeded"
**Solution:**
- Wait 1-2 minutes between batches
- Reduce batch size
- Spread generation over multiple days

### Issue: "Insufficient quota"
**Solution:**
- Check API usage: https://platform.openai.com/usage
- Verify payment method is valid
- Contact OpenAI support

### Issue: Generation fails repeatedly
**Solution:**
- Check prompt doesn't violate content policy
- Try simpler prompt
- Verify internet connection
- Check OpenAI status: https://status.openai.com

## Advanced Usage

### Custom Python Script

```python
from sora_video_generator import SoraVideoGenerator

# Initialize
generator = SoraVideoGenerator(output_dir="my_videos")

# Generate with custom settings
result = generator.generate_video(
    prompt="A cat playing piano in a jazz bar",
    duration=10,
    resolution="1080p_landscape",
    model="standard"
)

if result:
    print(f"Video saved to: {result['filepath']}")
    print(f"Cost: ${result['cost_estimate']:.2f}")
```

### Scheduled Automation

Create a cron job (Linux/Mac):
```bash
# Edit crontab
crontab -e

# Add daily generation at 2 AM
0 2 * * * cd /path/to/aivideogen && ./venv/bin/python sora_video_generator.py --prompts-file daily_prompts.txt
```

### Parallel Generation

For faster processing, run multiple instances:
```bash
# Terminal 1
python sora_video_generator.py --prompts-file batch1.txt --output-dir videos1 &

# Terminal 2
python sora_video_generator.py --prompts-file batch2.txt --output-dir videos2 &

# Terminal 3
python sora_video_generator.py --prompts-file batch3.txt --output-dir videos3 &
```

## Next Steps

1. **Plan your strategy** with `subscription_planner.py`
2. **Create your prompt library** organized by theme
3. **Start small** with 5-10 test videos
4. **Scale up** to daily batches
5. **Monitor and adjust** based on results
6. **Archive and organize** generated content

## Resources

- OpenAI Platform: https://platform.openai.com
- Sora Documentation: https://platform.openai.com/docs/guides/video-generation
- API Usage Dashboard: https://platform.openai.com/usage
- Community Forum: https://community.openai.com

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review error messages carefully
3. Check OpenAI status page
4. Consult OpenAI documentation
5. Ask in OpenAI community forum

---

**Ready to start?** Run the planner and generate your first test video!

```bash
# Plan your strategy
python subscription_planner.py --compare --schedule

# Generate your first video
python sora_video_generator.py --prompt "Your creative prompt here" --duration 10
```

Good luck maximizing your subscription!
