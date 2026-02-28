#!/usr/bin/env python3
"""
Power Analysis Video - Blackboard style with voice cloning.
Matches the teaching style of Combination.mpeg:
  - Black background
  - Yellow title with || separator
  - White typed text for definitions
  - Yellow Chalkduster handwriting appearing progressively
  - Small face cam overlay top-right
  - Cloned voice from voice_sample.wav
"""

import os, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageSequenceClip, AudioFileClip,
    concatenate_videoclips, VideoFileClip,
    CompositeVideoClip
)

# ─── Settings ─────────────────────────────────────────────────────────────────
W, H       = 1440, 800
FPS        = 24
OUTPUT     = "power_analysis_video_v2.mp4"
VOICE_WAV  = "videos/voice_sample.wav"
FACECAM    = "videos/facecam.mp4"
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))

# Colors
BLACK  = (0,   0,   0  )
WHITE  = (235, 235, 235)
YELLOW = (255, 222, 30 )
RED    = (255, 80,  80 )
GRAY   = (160, 160, 160)

# Layout
PAD_X      = 65
TITLE_Y    = 32
BODY_Y     = 105
LINE_H     = 62
TITLE_SZ   = 38
BODY_SZ    = 34
HW_SZ      = 36

# Face cam (top-right corner)
FC_W, FC_H = 200, 148
FC_X = W - FC_W - 12
FC_Y = 6

# ─── Fonts ────────────────────────────────────────────────────────────────────
def _try_fonts(candidates, size):
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

def font_title(size=TITLE_SZ):
    return _try_fonts([
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
    ], size)

def font_body(size=BODY_SZ):
    return _try_fonts([
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
    ], size)

def font_chalk(size=HW_SZ):
    return _try_fonts([
        '/System/Library/Fonts/Chalkduster.ttf',
        '/Library/Fonts/Chalkduster.ttf',
        '/System/Library/Fonts/ChalkboardSE.ttc',
        '/Library/Fonts/MarkerFelt.ttc',
        '/System/Library/Fonts/Chalkboard.ttc',
    ], size)

# ─── Face cam loader ──────────────────────────────────────────────────────────
_fc_frames = None

def get_facecam_frames():
    global _fc_frames
    if _fc_frames is not None:
        return _fc_frames
    fc_path = os.path.join(BASE_DIR, FACECAM)
    if not os.path.exists(fc_path):
        return None
    clip = VideoFileClip(fc_path)
    _fc_frames = [
        np.array(Image.fromarray(clip.get_frame(t)).resize((FC_W, FC_H)))
        for t in np.linspace(0, clip.duration - 0.1, int(clip.duration * FPS))
    ]
    clip.close()
    return _fc_frames

# ─── Frame renderer ───────────────────────────────────────────────────────────
def render_frame(title, typed_lines, hw_lines, hw_partial=None, fc_idx=0):
    """
    title       : str  — yellow title (e.g. "Power Analysis || Why It Matters")
    typed_lines : list of (text, color) — white monospace body text
    hw_lines    : list of (text, color) — fully revealed yellow handwritten lines
    hw_partial  : (text, n_chars, color) — currently-being-written line
    fc_idx      : int — which face cam frame to use
    """
    img  = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)

    ft = font_title()
    fb = font_body()
    fc = font_chalk()

    # ── Title ──────────────────────────────────────────────────────────────────
    if title:
        draw.text((PAD_X, TITLE_Y), title, fill=YELLOW, font=ft)

    # ── Typed body text ────────────────────────────────────────────────────────
    for i, (text, color) in enumerate(typed_lines):
        y = BODY_Y + i * LINE_H
        if y > H - 60:
            break
        draw.text((PAD_X, y), text, fill=color or WHITE, font=fb)

    # ── Handwritten lines ──────────────────────────────────────────────────────
    hw_start_y = BODY_Y + len(typed_lines) * LINE_H + 20

    for i, (text, color) in enumerate(hw_lines):
        y = hw_start_y + i * LINE_H
        if y > H - 60:
            break
        draw.text((PAD_X, y), text, fill=color or YELLOW, font=fc)

    # ── Currently-writing line (typewriter effect) ─────────────────────────────
    if hw_partial:
        text, n, color = hw_partial
        partial = text[:n]
        i = len(hw_lines)
        y = hw_start_y + i * LINE_H
        if y < H - 60:
            draw.text((PAD_X, y), partial, fill=color or YELLOW, font=fc)
            bbox = draw.textbbox((PAD_X, y), partial, font=fc)
            draw.line([bbox[2] + 3, y + 4, bbox[2] + 3, y + HW_SZ - 4],
                      fill=YELLOW, width=2)

    # ── Face cam overlay ───────────────────────────────────────────────────────
    fc_frames = get_facecam_frames()
    if fc_frames:
        idx = fc_idx % len(fc_frames)
        fc_img = Image.fromarray(fc_frames[idx])
        img.paste(fc_img, (FC_X, FC_Y))

    return np.array(img)

# ─── Build frames for one section ─────────────────────────────────────────────
def build_frames(title, typed_lines, hw_lines, duration_sec, fc_start=0):
    """
    Reveal typed_lines all at once, then reveal hw_lines char-by-char.
    Stretches to fit duration_sec.
    """
    frame_list = []
    fc_idx     = fc_start

    # First frame — show only title + typed text, no handwriting yet
    frame_list.append(render_frame(title, typed_lines, [], fc_idx=fc_idx))
    fc_idx += 1

    # Reveal each handwritten line character by character
    revealed_hw = []
    for line_text, line_color in hw_lines:
        if not line_text.strip():
            revealed_hw.append((line_text, line_color))
            frame_list.append(render_frame(title, typed_lines, revealed_hw, fc_idx=fc_idx))
            fc_idx += 1
            continue
        for c in range(1, len(line_text) + 1):
            frame_list.append(render_frame(
                title, typed_lines, revealed_hw,
                hw_partial=(line_text, c, line_color),
                fc_idx=fc_idx
            ))
            fc_idx += 1
        revealed_hw.append((line_text, line_color))

    # Hold on final frame
    hold = int(FPS * 0.5)
    final_f = render_frame(title, typed_lines, revealed_hw, fc_idx=fc_idx)
    frame_list += [final_f] * hold

    # Stretch to target duration
    n_target = max(1, int(duration_sec * FPS))
    indices  = np.linspace(0, len(frame_list) - 1, n_target).astype(int)
    return [frame_list[i] for i in indices], fc_idx

# ─── Voice cloning ────────────────────────────────────────────────────────────
def generate_voice(text, out_path, voice_sample):
    """Generate voice using macOS Rishi (Indian-English male) via say command."""
    try:
        aiff_path = out_path.replace(".mp3", ".aiff")
        result = os.system(f'say -v Rishi -r 175 -o "{aiff_path}" "{text}"')
        if result == 0 and os.path.exists(aiff_path):
            os.system(f'ffmpeg -i "{aiff_path}" "{out_path}" -y -loglevel error')
            os.remove(aiff_path)
            return True
        raise Exception("say command failed")
    except Exception as e:
        print(f"  macOS say failed ({e}), falling back to gTTS...")
        from gtts import gTTS
        gTTS(text, lang="en", slow=False).save(out_path)
        return False

# ─── Script ───────────────────────────────────────────────────────────────────
SCRIPT = [
    {
        "title": "Power Analysis || Why It Matters",
        "typed": [
            ("Power Analysis: Probability of detecting", WHITE),
            ("a real effect when one truly exists.", WHITE),
            ("", WHITE),
            ("A 2023 study claimed:", WHITE),
        ],
        "handwritten": [
            ("Rounded corners  -->  +55% click-through rate", YELLOW),
            ("", YELLOW),
            ("p-value = 0.037    'Statistically Significant!'", YELLOW),
            ("", YELLOW),
            ("But the study had only ~30 participants.", RED),
        ],
        "voiceover": (
            "A 2023 study published in a top academic journal claimed that "
            "rounded button corners increased click-through rates by 55 percent. "
            "The p-value was 0.037 — statistically significant. "
            "But the study had only around 30 participants. "
            "And that is a serious problem."
        ),
    },
    {
        "title": "Statistical Power ||",
        "typed": [
            ("Power = P( detecting a real effect )", WHITE),
            ("", WHITE),
            ("Standard target:   Power  >=  80%", WHITE),
            ("", WHITE),
            ("Power depends on:", WHITE),
        ],
        "handwritten": [
            ("  1.  Sample size     (bigger  =  more power)", YELLOW),
            ("  2.  Effect size     (bigger  =  easier to detect)", YELLOW),
            ("  3.  Alpha level     (alpha = 0.05)", YELLOW),
            ("", YELLOW),
            ("Small sample  =  low power  =  miss real effects", RED),
        ],
        "voiceover": (
            "Statistical power is the probability that your test correctly detects "
            "a real effect when one exists. "
            "The standard target is 80 percent power. "
            "Power depends on three things: your sample size, "
            "the effect size you're trying to detect, "
            "and your significance threshold alpha. "
            "A small sample means low power — you'll miss real effects."
        ),
    },
    {
        "title": "The Winner's Curse ||",
        "typed": [
            ("Underpowered study: most experiments fail.", WHITE),
            ("The few that reach p < 0.05 are flukes.", WHITE),
            ("", WHITE),
            ("Published result  =  extreme overestimate", WHITE),
        ],
        "handwritten": [
            ("Think of it like this:", YELLOW),
            ("", YELLOW),
            ("  You flip a coin 5 times, get 5 heads.", YELLOW),
            ("  You publish: 'coin always lands heads!'", YELLOW),
            ("", YELLOW),
            ("True effect was inflated by ~100x", RED),
        ],
        "voiceover": (
            "Here is the core problem — the Winner's Curse. "
            "When a study is underpowered, most experiments fail to find anything significant. "
            "The few experiments that do reach significance are extreme statistical flukes. "
            "So the result that gets published is always a massive overestimate of the true effect. "
            "In this case, the true effect was inflated by approximately 100 times."
        ),
    },
    {
        "title": "Replication Results ||",
        "typed": [
            ("Study              Sample    Effect    Significant?", GRAY),
            ("─" * 58,                               GRAY),
            ("Original  (2023)   n ~ 30    +55%      Yes  p=0.037", WHITE),
        ],
        "handwritten": [
            ("Replication 1:   n = 60,000+    ~0.5%    No", YELLOW),
            ("Replication 2:   n = 60,000+    ~0.3%    No", YELLOW),
            ("Replication 3:   n = 60,000+    ~0.6%    No", YELLOW),
            ("Evidoo Rep. 1:   n = 60,000+    ~0.4%    No", YELLOW),
            ("Evidoo Rep. 2:   n = 60,000+    ~0.2%    No", YELLOW),
            ("", YELLOW),
            ("Effect was 100x smaller. None were significant.", RED),
        ],
        "voiceover": (
            "Researchers then ran five high-powered replications, "
            "each with over 60,000 users — more than 2,000 times the original sample. "
            "Replication one: 0.5 percent — not significant. "
            "Replication two: 0.3 percent — not significant. "
            "And so on across all five studies. "
            "The effect was 100 times smaller than claimed, "
            "and none of the replications were statistically significant."
        ),
    },
    {
        "title": "Key Takeaways ||",
        "typed": [
            ("Always do power analysis BEFORE the experiment.", WHITE),
            ("", WHITE),
        ],
        "handwritten": [
            ("Steps:", YELLOW),
            ("  1. Define your minimum detectable effect  (MDE)", YELLOW),
            ("  2. Set  alpha = 0.05  and  power = 80%", YELLOW),
            ("  3. Calculate required sample size", YELLOW),
            ("", YELLOW),
            ("  n = 2 * ( Z_alpha + Z_beta )^2  /  d^2", YELLOW),
            ("", YELLOW),
            ("Be skeptical of big effects from small samples!", RED),
        ],
        "voiceover": (
            "So what is the key lesson? "
            "Always do power analysis before running your experiment. "
            "First, define the minimum effect that would actually matter to you. "
            "Second, set your alpha to 0.05 and target 80 percent power. "
            "Third, calculate how many participants you actually need. "
            "And always be skeptical of dramatic results from small studies. "
            "Power analysis is not optional — it is essential."
        ),
    },
]

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    tmp      = tempfile.mkdtemp()
    voice_p  = os.path.join(BASE_DIR, VOICE_WAV)
    clips    = []
    fc_idx   = 0

    print("Loading face cam frames...")
    get_facecam_frames()

    for i, section in enumerate(SCRIPT):
        label = section["title"]
        print(f"\n[{i+1}/{len(SCRIPT)}]  {label}")

        # Generate voice
        audio_path = os.path.join(tmp, f"vo_{i}.mp3")
        print("  Generating voice...")
        generate_voice(section["voiceover"], audio_path, voice_p)
        audio_clip = AudioFileClip(audio_path)
        duration   = audio_clip.duration + 0.3

        # Generate frames
        print("  Building frames...")
        frames, fc_idx = build_frames(
            section["title"],
            section["typed"],
            section["handwritten"],
            duration,
            fc_start=fc_idx,
        )

        # Combine
        video = ImageSequenceClip(frames, fps=FPS)
        video = video.with_audio(audio_clip)
        clips.append(video)

    print("\nConcatenating all sections...")
    final = concatenate_videoclips(clips, method="compose")

    print(f"Writing  ->  {OUTPUT}")
    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    print(f"\nDone!  Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
