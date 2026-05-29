#!/usr/bin/env python3
"""
Video Commentator - Lay AI voiceover commentary onto a match video.

Two ways to source the play-by-play:
  * --guide-audio / --guide-transcript : drive the LEAD commentary from a real
    spoken guide recording (transcribed, timestamped). Most accurate -- it
    captures the real goals, names and timing. (Recommended.)
  * otherwise: a vision model samples frames and detects events itself.

On top of the lead commentator (ElevenLabs, British, energy-scaled) it adds:
  * a daft, working-class SECOND commentator (OpenAI, steered accent) who
    interjects useless asides after the lead on notable moments;
  * a reactive crowd -- a varied stadium-din bed, anticipation swells on
    crosses/shots, groans on misses, and a roar on every goal;
  * a manual --events override and a global --lead time shift.

Needs OPENAI_API_KEY (vision/transcription/sidekick) and ELEVENLABS_API_KEY
(lead voice + crowd) in .env.
"""

import os
import re
import sys
import json
import time
import base64
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    import requests
except ImportError:
    print("Error: dependencies missing. Run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

GOAL_INTENSITY = 5
EL_VOICES = {  # voices in this account (GET /v1/voices)
    "george": "JBFqnCBsd6RMkjVDRZzb",  # british, warm, captivating (LEAD)
    "daniel": "onwK4e9ZLuTAKqWW03F9",  # british, steady broadcaster
    "james":  "fATgBRI8wg5KkDFg8vBd",  # british, smooth professional
    "bunty":  "FZkK3TvQ0pjyDmT8fzIW",  # young/punchy -- but Hindi-accented
    "prince": "nstAjY74EkciBLEg9uvD",  # cockney London lad (SIDEKICK)
    "announcer": "gU0LNdkMOQCOrPrwtbee",  # energetic British football announcer (LEAD)
}

# Whisper mishears -- correct names before they reach the commentary
NAME_FIXES = [(r"\bAn[eé]\b", "Ian"), (r"\bAine\b", "Ian"), (r"\bEnya\b", "Ian"),
              (r"\bNiren\b", "Nirun"),
              (r"\bClod(?:ie|y|i)\b", "Klody"),   # -> 'Klow-dee'
              (r"\bBrodie\b", "Brody"),
              (r"\bAbelite\b", "Abel"),
              (r"\bTom[aá][sš]\b", "Tomasz")]


def fix_names(text: str) -> str:
    for pat, repl in NAME_FIXES:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


# --------------------------------------------------------------------------- #
# ffmpeg helpers
# --------------------------------------------------------------------------- #
def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: ffmpeg/ffprobe not found. Install: brew install ffmpeg")
        sys.exit(1)


def probe_duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def has_audio_stream(video: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True)
    return "audio" in out.stdout


def media_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def extract_frames(video: Path, interval: float, out_dir: Path,
                   width: int = 768) -> List[Tuple[float, Path]]:
    duration = probe_duration(video)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: List[Tuple[float, Path]] = []
    t, idx = 0.0, 0
    while t < duration:
        fp = out_dir / f"frame_{idx:04d}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
             "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4",
             "-y", str(fp)], check=True)
        if fp.exists():
            frames.append((t, fp))
        t += interval
        idx += 1
    return frames


# --------------------------------------------------------------------------- #
# Guide-audio path: transcribe -> lead commentary cues
# --------------------------------------------------------------------------- #
def transcribe_guide(client: OpenAI, audio: Path, cache: Path) -> List[Dict]:
    if cache.exists():
        return json.loads(cache.read_text())
    with open(audio, "rb") as f:
        tr = client.audio.transcriptions.create(
            model="whisper-1", file=f, response_format="verbose_json",
            timestamp_granularities=["segment"])
    segs = tr.segments if hasattr(tr, "segments") else tr["segments"]
    out = [{"start": round(s.start, 1), "end": round(s.end, 1),
            "text": s.text.strip()} for s in segs]
    cache.write_text(json.dumps(out, indent=1))
    return out


def guide_to_cues(client: OpenAI, transcript: List[Dict], model: str) -> List[Dict]:
    system = (
        "You are turning a raw, rambling first-person football commentary "
        "transcript (timestamps in seconds) into polished, broadcast-style "
        "play-by-play for an excitable British LEAD commentator. KEEP the real "
        "player names and the real events, and follow the original timing "
        "closely. Clean the rambling into punchy, natural broadcast lines.\n\n"
        "Return ONLY JSON: {\"cues\":[{\"time\":<sec number>,\"event\":\"<goal|"
        "miss|shot|save|cross|run|buildup|color>\",\"intensity\":<1-5>,\"text\":"
        "\"<spoken line>\"}]}.\n"
        "intensity: 5=goal, 4=miss/shot/save/big chance, 3=promising attack or "
        "cross, 2=midfield, 1=lull. Goal lines must be exclamatory. Produce at "
        "most one cue per transcript segment (merge adjacent rambles). Keep each "
        "line short enough to speak before the next cue (~3 words/sec).")
    blob = "\n".join(f"[{s['start']:.1f}] {s['text']}" for s in transcript)
    resp = client.chat.completions.create(
        model=model, response_format={"type": "json_object"}, temperature=0.7,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": blob}])
    data = json.loads(resp.choices[0].message.content)
    cues = []
    for c in data.get("cues", []) or []:
        if "time" not in c or not c.get("text"):
            continue
        cues.append({"time": max(0.0, float(c["time"])), "text": c["text"].strip(),
                     "event": str(c.get("event", "color")).lower(),
                     "intensity": int(c.get("intensity", 2)),
                     "voice": "lead", "manual": False})
    cues.sort(key=lambda c: c["time"])
    return cues


# --------------------------------------------------------------------------- #
# Second commentator (daft, working-class) -- reacts to the lead
# --------------------------------------------------------------------------- #
def _data_url(image_path: Path) -> str:
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


VISION_ROSTER = (
    "This is a recreational match: the ORANGE-bibbed side versus the side NOT in "
    "orange (a mix of blue, white and dark tops). Regulars in this group -- use a "
    "name only if it fits naturally, otherwise say 'the orange side' / 'a lad in "
    "orange' / 'the side not in orange': Quentin (a Frenchman, butt of "
    "late-arrival jokes), Blake and Walter (both NOT on orange), Brody, Graham "
    "(wears a ridiculous white headband; capable of a wonder goal or a shocking "
    "miss), Klody (spelt 'Klody', said Klow-dee), Milton, Soren, Tomasz, Victor, "
    "Ricky, Shane, Abel, Nirun, Ian (sometimes baby blue), Edwin, Marcos, Tom in goal."
)

VISION_SYSTEM = (
    "You are an elite, excitable British Premier-League football commentator. You "
    "are shown still frames from one continuous match video, each labelled with "
    "its timestamp in seconds. Call the MOMENTS that matter (attacks, runs, "
    "crosses, shots, saves, GOALS, turnovers) -- do NOT narrate every frame.\n\n"
    + VISION_ROSTER +
    "\n\nReturn ONLY JSON: {\"cues\":[{\"time\":<sec>,\"event\":\"<kickoff|buildup|"
    "run|cross|shot|save|goal|turnover|color>\",\"intensity\":<1-5>,\"text\":"
    "\"<short spoken line>\"}],\"summary\":\"<running recap>\"}\n"
    "intensity: 5=goal, 4=shot/save/big chance, 3=promising attack/cross, "
    "2=midfield, 1=lull. Be CONSERVATIVE about goals -- only event \"goal\" when "
    "the ball is clearly in the net or players celebrate; otherwise shot/save. "
    "Roughly one cue every 10-15 seconds. Keep each line short enough to say in "
    "the gap (~3 words/sec). Lean on team colours; sprinkle the odd name for "
    "flavour; never invent a scoreline. British spellings."
)


def generate_commentary_vision(client: OpenAI, frames: List[Tuple[float, Path]],
                               model: str, chunk_size: int, min_gap: float = 6.0,
                               detail: str = "low") -> List[Dict]:
    cues: List[Dict] = []
    summary = ""
    total = (len(frames) + chunk_size - 1) // chunk_size
    for ci, chunk in enumerate(_chunks(frames, chunk_size), 1):
        print(f"  [vision {ci}/{total}] {chunk[0][0]:.0f}-{chunk[-1][0]:.0f}s "
              f"({len(chunk)} frames)...")
        content: List[Dict] = [{"type": "text", "text":
            f"Continuity so far: {summary or '(start of match)'}\nThe next "
            f"{len(chunk)} frames in order; return JSON cues for the moments that matter."}]
        for ts, fp in chunk:
            content.append({"type": "text", "text": f"[t={ts:.1f}s]"})
            content.append({"type": "image_url",
                            "image_url": {"url": _data_url(fp), "detail": detail}})
        resp = client.chat.completions.create(
            model=model, response_format={"type": "json_object"}, temperature=0.8,
            messages=[{"role": "system", "content": VISION_SYSTEM},
                      {"role": "user", "content": content}])
        try:
            data = json.loads(resp.choices[0].message.content)
        except (json.JSONDecodeError, TypeError):
            print("    ! parse fail; skipping chunk")
            continue
        for c in data.get("cues", []) or []:
            if "time" not in c or not c.get("text"):
                continue
            cues.append({"time": max(0.0, float(c["time"])), "text": str(c["text"]).strip(),
                         "event": str(c.get("event", "color")).lower(),
                         "intensity": int(c.get("intensity", 2)),
                         "voice": "lead", "manual": False})
        summary = data.get("summary", summary)
    cues.sort(key=lambda c: c["time"])
    kept, last = [], -999.0          # thin so lead lines don't overlap
    for c in cues:
        if c["intensity"] >= 4 or (c["time"] - last) >= min_gap:
            kept.append(c)
            last = c["time"]
    return kept


def make_sidekick_quips(client: OpenAI, count: int, model: str) -> List[Dict]:
    """A pool of standalone, ridiculous one-liners (not tied to specific plays)."""
    system = (
        f"Write {count} short, ridiculous, funny one-liner quips from a daft, "
        "eager, working-class British football co-commentator. They can be about "
        "ANYTHING -- the match in general, the weather, pies, his mate Dave, his "
        "nan, random tangents -- and need NOT reference any specific play. Each "
        "max ~10 words, punchy, standalone, exclaimable, varied (don't repeat the "
        "same subject). Broad working-class vernacular (innit, mate, blimey, lovely "
        "that). Return ONLY JSON: {\"lines\":[\"...\", ...]}.")
    resp = client.chat.completions.create(
        model=model, response_format={"type": "json_object"}, temperature=1.0,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": "Give me the quips."}])
    lines = json.loads(resp.choices[0].message.content).get("lines", []) or []
    return [{"text": str(l).strip(), "event": "color", "intensity": 4,
             "voice": "sidekick", "manual": False} for l in lines if str(l).strip()]


def _busy_intervals(cues: List[Dict]) -> List[Tuple[float, float]]:
    iv = sorted((c["time"], c["time"] + c.get("audio_dur", 3.0)) for c in cues)
    merged: List[Tuple[float, float]] = []
    for s, e in iv:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def place_sidekicks(anchored: List[Dict], pool: List[Dict], lead: List[Dict],
                    duration: float, margin: float = 0.3,
                    min_sep: float = 9.0) -> List[Dict]:
    """Place sidekick lines ONLY where the lead is silent, at most ONE per gap,
    and never within `min_sep` of another sidekick line -- so he only ever quips
    one at a time (user rule). Anchored lines go near their target; pool quips
    fill the roomiest remaining gaps. Unfittable lines are dropped."""
    busy = _busy_intervals(lead)
    free, prev = [], 0.0           # free = list of [start, end, used?]
    for s, e in busy:
        if s - prev > 0:
            free.append([prev, s, False])
        prev = max(prev, e)
    if duration - prev > 0:
        free.append([prev, duration, False])

    placed: List[Dict] = []

    def put(cue: Dict, target: Optional[float]) -> bool:
        need = cue.get("audio_dur", 2.0) + 2 * margin
        if target is not None:                       # nearest gap to the target
            order = sorted(range(len(free)), key=lambda i: (
                0 if free[i][0] <= target <= free[i][1] else 1,
                abs(free[i][0] - target)))
        else:                                         # biggest gap first (spread)
            order = sorted(range(len(free)),
                           key=lambda i: free[i][1] - free[i][0], reverse=True)
        for i in order:
            seg = free[i]
            if seg[2]:                                # one quip per gap
                continue
            start = seg[0]
            if target is not None and seg[0] <= target <= seg[1]:
                start = max(seg[0], target)
            t = start + margin
            if seg[1] - start >= need and all(abs(t - p["time"]) >= min_sep
                                              for p in placed):
                cue["time"] = t
                seg[2] = True
                placed.append(cue)
                return True
        return False

    for c in anchored:
        put(c, c.get("time"))
    for c in pool:
        put(c, None)
    return placed


# --------------------------------------------------------------------------- #
# Manual events / spacing / timing
# --------------------------------------------------------------------------- #
def load_manual_events(path: Path) -> List[Dict]:
    out = []
    for e in json.loads(path.read_text()):
        out.append({"time": float(e["time"]), "text": str(e.get("text", "")).strip(),
                    "event": str(e.get("event", "color")).lower(),
                    "intensity": int(e.get("intensity",
                                           GOAL_INTENSITY if e.get("event") == "goal" else 4)),
                    "voice": str(e.get("voice", "lead")).lower(), "manual": True})
    return out


def merge_events(auto: List[Dict], manual: List[Dict], window: float) -> List[Dict]:
    kept = [a for a in auto
            if all(abs(a["time"] - m["time"]) > window for m in manual)]
    merged = kept + manual
    merged.sort(key=lambda c: c["time"])
    return merged


def apply_lead(cues: List[Dict], lead: float) -> None:
    for c in cues:
        c["time"] = max(0.0, c["time"] - lead)


# --------------------------------------------------------------------------- #
# Text-to-speech
# --------------------------------------------------------------------------- #
def energy_instruction(intensity: int) -> str:
    base = ("Speak as an energetic British Premier-League football commentator "
            "with a natural English accent.")
    if intensity >= GOAL_INTENSITY:
        return base + " THIS IS A GOAL -- explode, shout the call, peak energy."
    if intensity == 4:
        return base + " High excitement -- fast, loud, a big chance."
    if intensity == 3:
        return base + " Lively and engaged, building anticipation."
    return base + " Measured and conversational, setting the scene."


def el_voice_settings(intensity: int) -> Dict:
    """Max-emotion profile for v2 models: very low stability + high style."""
    table = {5: (0.12, 1.00), 4: (0.18, 0.88), 3: (0.28, 0.72)}
    stab, style = table.get(intensity, (0.38, 0.58))
    return {"stability": stab, "similarity_boost": 0.75,
            "style": style, "use_speaker_boost": True}


def _el_post(url: str, body: Dict, timeout: int = 180, tries: int = 4):
    """POST to ElevenLabs with retries -- the API occasionally returns a
    transient 401/429/5xx mid-session; don't let one blip kill a whole render."""
    key = os.getenv("ELEVENLABS_API_KEY")
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    for i in range(tries):
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if r.status_code == 200:
            return r
        if r.status_code in (401, 429, 500, 502, 503, 529) and i < tries - 1:
            time.sleep(2 * (i + 1))
            continue
        r.raise_for_status()
    r.raise_for_status()
    return r


def emotion_tag(event: str, intensity: int) -> str:
    """Inline audio tag for eleven_v3. Pushed shoutier per user request -- both
    commentators shout on goals, misses and any real chance."""
    if event == "goal" or intensity >= GOAL_INTENSITY:
        return "[shouting] "
    if event == "miss" or intensity >= 4 or event in ("shot", "save", "cross"):
        return "[shouting] "
    if intensity >= 3:
        return "[excited] "
    return ""


def tts_elevenlabs(text: str, out_path: Path, voice_id: str, model_id: str,
                   intensity: int, event: str = "color",
                   tag: Optional[str] = None, stability: Optional[float] = None) -> None:
    """tag/stability let a caller override the auto v3 emotion (e.g. the sidekick
    wants a crisper, less-shouty 'Natural' delivery rather than 'Creative')."""
    key = os.getenv("ELEVENLABS_API_KEY")
    if model_id == "eleven_v3":
        t = tag if tag is not None else emotion_tag(event, intensity)
        text = t + text
        # 'Natural' stability (0.5) keeps the British accent locked -- 'Creative'
        # (0.0) drifted the accent American on shouted lines.
        stab = stability if stability is not None else 0.5
        settings = {"stability": stab, "similarity_boost": 0.75,
                    "use_speaker_boost": True}
    else:
        settings = el_voice_settings(intensity)
    r = _el_post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        "?output_format=mp3_44100_128",   # 192k is gated to higher tiers (403)
        {"text": text, "model_id": model_id, "voice_settings": settings})
    out_path.write_bytes(r.content)


def tts_openai(client: OpenAI, text: str, out_path: Path, voice: str,
               model: str, instructions: Optional[str]) -> None:
    kwargs = dict(model=model, voice=voice, input=text, response_format="mp3")
    if instructions and model not in ("tts-1", "tts-1-hd"):
        kwargs["instructions"] = instructions
    with client.audio.speech.with_streaming_response.create(**kwargs) as resp:
        resp.stream_to_file(str(out_path))


# --------------------------------------------------------------------------- #
# Crowd sound effects (ElevenLabs) + reactive placements
# --------------------------------------------------------------------------- #
def elevenlabs_sfx(text: str, out_path: Path, duration: Optional[float] = None,
                   loop: bool = False, influence: float = 0.5) -> None:
    body = {"text": text, "model_id": "eleven_text_to_sound_v2",
            "prompt_influence": influence, "loop": loop}
    if duration:
        body["duration_seconds"] = max(0.5, min(30.0, duration))
    r = _el_post(
        "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
        body)
    out_path.write_bytes(r.content)


def build_varied_bed(variants: List[Path], full_path: Path, duration: float) -> None:
    """Concatenate the ambience variants, then loop that out to full length so
    the bed is less obviously repetitive than a single short loop."""
    concat = full_path.with_name("bed_concat.mp3")
    lst = full_path.with_name("bed_list.txt")
    lst.write_text("".join(f"file '{v.resolve()}'\n" for v in variants))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "libmp3lame", "-b:a", "128k", str(concat)], check=True)
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(concat),
                    "-t", f"{duration:.3f}", "-c:a", "libmp3lame", "-b:a", "128k",
                    str(full_path)], check=True)


def reactive_sfx_inserts(lead_cues: List[Dict], sfx: Dict[str, Path]) -> List[Dict]:
    """Map lead events to crowd reactions: roar on goals, swell on chances,
    groan on misses. Each carries fades so it blends with the bed (no abrupt
    cut-in/out) -- longer tails on the goal roar."""
    dur = {k: media_duration(v) for k, v in sfx.items()}
    inserts = []
    for c in lead_cues:
        ev, it = c["event"], c["intensity"]
        if ev == "goal" or it >= GOAL_INTENSITY:
            inserts.append({"path": sfx["roar"], "time": c["time"], "volume": 0.9,
                            "dur": dur["roar"], "fade_in": 0.5, "fade_out": 2.0,
                            "mono": True})
        elif ev == "miss":
            inserts.append({"path": sfx["groan"], "time": c["time"] + 0.4,
                            "volume": 0.7, "dur": dur["groan"],
                            "fade_in": 0.5, "fade_out": 1.4, "mono": True})
        elif ev in ("cross", "shot", "save") or it >= 4:
            inserts.append({"path": sfx["rise"], "time": max(0.0, c["time"] - 0.3),
                            "volume": 0.5, "dur": dur["rise"],
                            "fade_in": 0.4, "fade_out": 1.2, "mono": True})
    return inserts


# --------------------------------------------------------------------------- #
# Subtitles + generic mux
# --------------------------------------------------------------------------- #
def _srt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: List[Dict], path: Path, total: float) -> None:
    cues = sorted(cues, key=lambda c: c["time"])
    lines = []
    for i, c in enumerate(cues):
        start = c["time"]
        end = cues[i + 1]["time"] if i + 1 < len(cues) else total
        end = min(end, start + c.get("audio_dur", 4.0) + 0.5, total)
        who = "2" if c.get("voice") == "sidekick" else "1"
        lines.append(f"{i + 1}\n{_srt_ts(start)} --> {_srt_ts(max(end, start + 0.5))}"
                     f"\n[{who}] {c['text']}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def mux(video: Path, out_path: Path, duration: float, keep_original: bool,
        bed_path: Optional[Path], bed_vol: float, inserts: List[Dict],
        duck: float = 0.22) -> None:
    """inserts: list of {path, time(seconds), volume}. Mixed over an optional
    full-length bed and the (ducked) original audio."""
    in_args = ["-i", str(video), "-f", "lavfi", "-t", f"{duration:.3f}",
               "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    idx = 2
    filt: List[str] = []
    labels = ["[1:a]"]

    if keep_original and has_audio_stream(video):
        filt.append(f"[0:a]volume={duck}[orig]")
        labels.append("[orig]")
    if bed_path:
        in_args += ["-i", str(bed_path)]
        filt.append(f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,"
                    f"volume={bed_vol}[bed]")
        labels.append("[bed]")
        idx += 1
    for i, ins in enumerate(inserts):
        in_args += ["-i", str(ins["path"])]
        ms = int(round(max(0.0, ins["time"]) * 1000))
        # SFX: sum to mono then re-spread to stereo -> kills the 'phasey' swoosh
        layout = ("aformat=channel_layouts=mono,aformat=channel_layouts=stereo"
                  if ins.get("mono") else "aformat=channel_layouts=stereo")
        chain = f"[{idx}:a]aresample=44100,{layout},volume={ins['volume']}"
        md = ins.get("max_dur")
        if md:   # trim the tail + tiny fade so it can't run into the next cue
            chain += (f",atrim=0:{md:.2f},asetpts=N/SR/TB,"
                      f"afade=t=out:st={max(0.0, md - 0.12):.2f}:d=0.12")
        fi, fo, dur = ins.get("fade_in", 0), ins.get("fade_out", 0), ins.get("dur")
        if fi:
            chain += f",afade=t=in:st=0:d={fi}"
        if fo and dur and dur > fo:
            chain += f",afade=t=out:st={dur - fo:.2f}:d={fo}"
        chain += f",adelay={ms}:all=1[x{i}]"
        filt.append(chain)
        labels.append(f"[x{i}]")
        idx += 1
    filt.append("".join(labels) +
                f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0[mix]")
    filt.append("[mix]alimiter=limit=0.95[aout]")

    cmd = ["ffmpeg", "-y", *in_args, "-filter_complex", ";".join(filt),
           "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac",
           "-b:a", "192k", "-shortest", str(out_path)]
    subprocess.run(cmd, check=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser(description="AI voiceover commentary for a video")
    p.add_argument("--video", required=True)
    p.add_argument("--guide-audio", type=str, default=None,
                   help="Spoken guide recording to drive the lead commentary")
    p.add_argument("--guide-transcript", type=str, default=None,
                   help="Pre-made transcript JSON [{start,end,text}] (skips STT)")
    p.add_argument("--events", type=str, default=None,
                   help="JSON manual events {time,event,intensity,text}")
    p.add_argument("--lead", type=float, default=0.0,
                   help="Shift every cue this many seconds earlier (default: 0)")
    p.add_argument("--sidekick", dest="sidekick", action="store_true", default=True,
                   help="Add the daft second commentator (default on)")
    p.add_argument("--no-sidekick", dest="sidekick", action="store_false")
    p.add_argument("--sidekick-count", type=int, default=14,
                   help="Size of the quip pool; one per lead-silent gap, spaced "
                        ">=9s apart (default: 14)")
    # lead voice (ElevenLabs)
    p.add_argument("--el-voice", type=str, default="announcer",
                   help="Lead voice: announcer/george/daniel/james or a raw voice_id")
    p.add_argument("--el-model", type=str, default="eleven_v3",
                   help="ElevenLabs model (eleven_v3 = most expressive, tag-driven)")
    # sidekick voice (ElevenLabs -- clearly different person from the lead)
    p.add_argument("--voice2", type=str, default="prince",
                   help="ElevenLabs sidekick voice: prince (cockney)/bunty or id")
    p.add_argument("--tts-model", type=str, default="gpt-4o-mini-tts")
    # vision fallback
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--min-gap", type=float, default=6.0)
    p.add_argument("--vision-model", type=str, default="gpt-4o")
    p.add_argument("--text-model", type=str, default="gpt-4o")
    p.add_argument("--chunk-size", type=int, default=18)
    # crowd + mix
    p.add_argument("--crowd", dest="crowd", action="store_true", default=True)
    p.add_argument("--no-crowd", dest="crowd", action="store_false")
    p.add_argument("--crowd-volume", type=float, default=0.35)
    p.add_argument("--narration-volume", type=float, default=1.4)
    p.add_argument("--sidekick-volume", type=float, default=1.25)
    p.add_argument("--keep-original-audio", action="store_true")
    p.add_argument("--output", type=str, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    _require_ffmpeg()
    video = Path(args.video).expanduser()
    if not video.exists():
        print(f"Error: video not found: {video}")
        sys.exit(1)
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in .env.")
        sys.exit(1)
    if (args.crowd or True) and not args.dry_run and not os.getenv("ELEVENLABS_API_KEY"):
        print("Error: ELEVENLABS_API_KEY needed in .env for the lead voice/crowd.")
        sys.exit(1)

    client = OpenAI()
    duration = probe_duration(video)
    out = Path(args.output) if args.output else \
        video.with_name(f"{video.stem}_commentary.mp4")
    work = video.with_name(f"{video.stem}_work")
    frames_dir, audio_dir, sfx_dir = work / "frames", work / "audio", work / "sfx"
    for d in (audio_dir, sfx_dir):
        d.mkdir(parents=True, exist_ok=True)
    el_voice = EL_VOICES.get(args.el_voice.lower(), args.el_voice)

    print(f"\n{'=' * 78}\nVIDEO COMMENTATOR (v4)\n{'=' * 78}")
    print(f"Video:     {video}  ({duration:.0f}s)")
    src = (args.guide_transcript or args.guide_audio
           or (f"events script ({args.events})" if args.events else "vision detection"))
    print(f"Source:    {src}")
    print(f"Lead:      ElevenLabs {args.el_voice} | Sidekick: "
          f"{'ElevenLabs ' + args.voice2 if args.sidekick else 'off'}")
    print(f"Crowd:     {'reactive @ ' + str(args.crowd_volume) if args.crowd else 'off'}"
          f" | lead vol {args.narration_volume} | lead shift {args.lead}s")
    print(f"{'=' * 78}\n")

    # ---- manual events: lead overrides + anchored sidekick lines ----
    manual_lead, manual_side = [], []
    if args.events:
        manual = load_manual_events(Path(args.events).expanduser())
        manual_lead = [m for m in manual if m["voice"] == "lead"]
        manual_side = [m for m in manual if m["voice"] == "sidekick"]

    # ---- lead commentary cues ----
    if args.guide_transcript or args.guide_audio:
        print("[1/6] Building lead commentary from guide audio...")
        if args.guide_transcript:
            transcript = json.loads(Path(args.guide_transcript).expanduser().read_text())
        else:
            transcript = transcribe_guide(
                client, Path(args.guide_audio).expanduser(),
                work / "guide_transcript.json")
            print(f"      transcribed {len(transcript)} segments")
        lead_cues = guide_to_cues(client, transcript, args.text_model)
        if manual_lead:
            # light window keeps the guide's build-up; then drop any AUTO goal a
            # pinned manual goal already covers (guide goals sit a few s early)
            lead_cues = merge_events(lead_cues, manual_lead, window=5.0)
            mgoals = [m["time"] for m in manual_lead
                      if m["event"] == "goal" or m["intensity"] >= GOAL_INTENSITY]
            lead_cues = [c for c in lead_cues if not (
                (not c.get("manual"))
                and (c["event"] == "goal" or c["intensity"] >= GOAL_INTENSITY)
                and any(abs(c["time"] - g) <= 16 for g in mgoals))]
            print(f"      merged {len(manual_lead)} lead + {len(manual_side)} sidekick event(s)")
    elif manual_lead:
        print("[1/6] Building lead commentary from --events (script-driven)...")
        lead_cues = sorted(manual_lead, key=lambda c: c["time"])
        print(f"      {len(manual_lead)} lead + {len(manual_side)} sidekick event(s)")
    else:
        print("[1/6] Detecting events from frames (vision baseline)...")
        frames = extract_frames(video, args.interval, frames_dir)
        print(f"      {len(frames)} frames")
        lead_cues = generate_commentary_vision(client, frames, args.vision_model,
                                                args.chunk_size, args.min_gap)
        if manual_lead:
            lead_cues = merge_events(lead_cues, manual_lead, window=9.0)

    for c in lead_cues:                       # correct Whisper name mishears
        c["text"] = fix_names(c["text"])
    apply_lead(lead_cues, args.lead)
    goals = [c for c in lead_cues if c["event"] == "goal" or c["intensity"] >= GOAL_INTENSITY]
    print(f"      {len(lead_cues)} lead cues ({len(goals)} goals):")
    for c in lead_cues:
        tag = "GOAL" if c in goals else f"i{c['intensity']}"
        print(f"       {c['time']:6.1f}s {tag:>5}  {c['text'][:64]}")

    if args.dry_run:
        write_srt(lead_cues, out.with_suffix(".srt"), duration)
        out.with_suffix(".commentary.txt").write_text(
            "\n".join(f"[{c['time']:.1f}s] {c['text']}" for c in lead_cues))
        print(f"\nDry run complete (lead script + .srt next to {out.name}).")
        return

    # ---- TTS: lead voice (ElevenLabs) ----
    print("[2/6] Synthesizing lead voice (ElevenLabs)...")
    for i, c in enumerate(lead_cues):
        clip = audio_dir / f"lead_{i:04d}.mp3"
        tts_elevenlabs(c["text"], clip, el_voice, args.el_model, c["intensity"],
                       c["event"])
        c["audio_path"], c["audio_dur"] = clip, media_duration(clip)
        print(f"      lead {i + 1}/{len(lead_cues)} ({c['audio_dur']:.1f}s)")
    # cap each lead clip so its tail can't bleed into the next lead cue
    # (TTS length jitters run-to-run; this guarantees no lead-vs-lead overlap)
    ls = sorted(lead_cues, key=lambda c: c["time"])
    for i, c in enumerate(ls):
        nxt = ls[i + 1]["time"] if i + 1 < len(ls) else duration
        gap = nxt - c["time"] - 0.05
        if 1.0 <= gap < c.get("audio_dur", 0):
            c["max_dur"] = gap

    # ---- sidekick: generate, place after lead, TTS (OpenAI) ----
    sidekick_cues: List[Dict] = []
    if args.sidekick:
        print("[3/6] Writing & voicing the eager cockney sidekick (ElevenLabs)...")
        side_voice = EL_VOICES.get(args.voice2.lower(), args.voice2)
        pool = make_sidekick_quips(client, args.sidekick_count, args.text_model)
        allside = manual_side + pool      # anchored manual lines + random pool
        for i, c in enumerate(allside):
            clip = audio_dir / f"side_{i:04d}.mp3"
            # crisper, less-shouty delivery: 'excited' (not shouting) + Natural stability
            tts_elevenlabs(c["text"], clip, side_voice, args.el_model, 4, "color",
                           tag="[excited] ", stability=0.5)
            c["audio_path"], c["audio_dur"] = clip, media_duration(clip)
        sidekick_cues = place_sidekicks(manual_side, pool, lead_cues, duration)
        print(f"      placed {len(sidekick_cues)}/{len(allside)} quips in lead-silent gaps")
        for c in sorted(sidekick_cues, key=lambda c: c["time"]):
            mark = "*" if c.get("manual") else " "
            print(f"     {mark}side @ {c['time']:6.1f}s: {c['text'][:50]}")
    else:
        print("[3/6] Sidekick disabled")

    all_cues = lead_cues + sidekick_cues
    write_srt(all_cues, out.with_suffix(".srt"), duration)
    out.with_suffix(".commentary.txt").write_text(
        "\n".join(f"[{c['time']:.1f}s][{c['voice']}] {c['text']}"
                  for c in sorted(all_cues, key=lambda c: c["time"])))

    # ---- crowd: varied bed + reactive SFX ----
    bed_path = None
    sfx_inserts: List[Dict] = []
    if args.crowd:
        print("[4/6] Generating reactive crowd SFX (ElevenLabs)...")
        v1, v2 = sfx_dir / "bed_a.mp3", sfx_dir / "bed_b.mp3"
        elevenlabs_sfx("A vast packed English Premier League stadium, tens of "
                       "thousands of fans, a deafening continuous wall of noise, "
                       "roaring and singing terrace chants, huge cavernous "
                       "atmosphere, no music.", v1, duration=30.0, loop=True)
        elevenlabs_sfx("A massive football terrace in full voice, fans loudly "
                       "singing and chanting in unison with drums, relentless "
                       "English Premier League atmosphere, no music.",
                       v2, duration=30.0, loop=True)
        bed_path = sfx_dir / "crowd_bed_full.mp3"
        build_varied_bed([v1, v2], bed_path, duration)
        sfx = {"rise": sfx_dir / "crowd_rise.mp3",
               "groan": sfx_dir / "crowd_groan.mp3",
               "roar": sfx_dir / "goal_roar.mp3"}
        elevenlabs_sfx("A football crowd rising in anticipation, oohs swelling as an "
                       "attack builds towards goal.", sfx["rise"], duration=4.0)
        elevenlabs_sfx("A large football crowd letting out a deep collective groan "
                       "and sigh of disappointment as a clear chance is missed; dry, "
                       "clean, close, no echo, no reverb, no music.",
                       sfx["groan"], duration=3.5, influence=0.6)
        elevenlabs_sfx("An enormous stadium crowd erupting into a deafening roar to "
                       "celebrate a goal.", sfx["roar"], duration=7.0)
        sfx_inserts = reactive_sfx_inserts(lead_cues, sfx)
        print(f"      bed (2 variants looped) + {len(sfx_inserts)} reactive hits")
    else:
        print("[4/6] Crowd disabled")

    # ---- assemble all audio inserts ----
    print("[5/6] Assembling audio layers...")
    inserts: List[Dict] = []
    for c in all_cues:
        vol = args.narration_volume if c["voice"] == "lead" else args.sidekick_volume
        ins = {"path": c["audio_path"], "time": c["time"], "volume": vol}
        if c.get("max_dur"):
            ins["max_dur"] = c["max_dur"]
        inserts.append(ins)
    inserts += sfx_inserts

    print("[6/6] Muxing onto video...")
    mux(video, out, duration, args.keep_original_audio, bed_path,
        args.crowd_volume, inserts)

    print(f"\n{'=' * 78}\n✓ Done: {out}")
    print(f"  subtitles: {out.with_suffix('.srt')}")
    print(f"  work dir:  {work}\n{'=' * 78}\n")


if __name__ == "__main__":
    main()
