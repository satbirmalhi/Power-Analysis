#!/usr/bin/env python3
"""
Power Analysis Video Generator
Style: Writing on a notepad with voiceover narration
"""

import os, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy import ImageSequenceClip, AudioFileClip, concatenate_videoclips

# ─── Settings ─────────────────────────────────────────────────────────────────
W, H       = 1280, 720
FPS        = 24
OUTPUT     = "power_analysis_video.mp4"

BG_COLOR   = (255, 252, 210)      # cream notepad
LINE_COLOR = (173, 216, 230)      # light blue ruled lines
MARGIN_CLR = (210, 45,  45)       # red left margin
INK        = (15,  25,  100)      # dark blue pen ink
TITLE_INK  = (150, 0,   0)        # red for headings
BIND_COLOR = (200, 200, 200)      # spiral binding bar
RING_COLOR = (160, 160, 160)

MARGIN_X   = 140
TOP_Y      = 138
LINE_H     = 56
FONT_SZ    = 33
TITLE_SZ   = 44
N_LINES    = 11

# ─── Fonts ────────────────────────────────────────────────────────────────────
def load_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

FONT       = load_font(FONT_SZ)
FONT_TITLE = load_font(TITLE_SZ)

# ─── Draw notepad background ──────────────────────────────────────────────────
def draw_background(draw):
    draw.rectangle([0, 0, W, H], fill=BG_COLOR)

    # Spiral binding bar at top
    draw.rectangle([0, 0, W, 68], fill=BIND_COLOR)
    for x in range(35, W, 48):
        draw.ellipse([x - 15, 30, x + 15, 72],
                     fill=RING_COLOR, outline=(110, 110, 110), width=2)

    # Red margin line
    draw.line([MARGIN_X - 18, 68, MARGIN_X - 18, H - 20],
              fill=MARGIN_CLR, width=2)

    # Ruled horizontal lines
    for i in range(N_LINES + 1):
        y = TOP_Y + i * LINE_H
        if y < H - 20:
            draw.line([MARGIN_X - 18, y, W - 40, y], fill=LINE_COLOR, width=1)

# ─── Render a single frame ────────────────────────────────────────────────────
def render_frame(revealed_lines, last_n_chars):
    """
    revealed_lines : list of (text, is_title) — fully revealed lines
    last_n_chars   : how many chars of the NEXT line to show (typewriter effect)
    """
    img  = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_background(draw)

    lines_to_draw = list(revealed_lines)

    for i, (text, is_title) in enumerate(lines_to_draw):
        y  = TOP_Y + i * LINE_H - 40
        if y > H - 50:
            break
        ff = FONT_TITLE if is_title else FONT
        cl = TITLE_INK  if is_title else INK
        draw.text((MARGIN_X, y), text, fill=cl, font=ff)

    return np.array(img)

# ─── Build frames for one section ────────────────────────────────────────────
def build_frames(lines, duration_sec):
    """
    lines        : list of (text, is_title)
    duration_sec : target duration in seconds
    Returns list of numpy frames.
    """
    revealed = []
    frame_list = []

    for text, is_title in lines:
        if not text.strip():
            revealed.append((text, is_title))
            frame_list.append(render_frame(revealed, len(text)))
            continue

        # Reveal character by character
        for c in range(1, len(text) + 1):
            partial = text[:c]
            frame_list.append(render_frame(revealed + [(partial, is_title)], c))

        revealed.append((text, is_title))

    # Hold on the final frame for 0.5 s
    hold_frames = int(FPS * 0.5)
    final_frame  = render_frame(revealed, 0)
    frame_list  += [final_frame] * hold_frames

    # Stretch / compress to fit target duration exactly
    n_target = max(1, int(duration_sec * FPS))
    indices  = np.linspace(0, len(frame_list) - 1, n_target).astype(int)
    return [frame_list[i] for i in indices]

# ─── Video script ─────────────────────────────────────────────────────────────
SCRIPT = [
    {
        "voiceover": (
            "A 2023 study published in a top journal claimed that "
            "rounded button corners increased click-through rates by 55 percent. "
            "Impressive — but they were completely wrong. Here's why it matters."
        ),
        "lines": [
            ("WHY MOST A/B TESTS LIE TO YOU", True),
            ("", False),
            ("A 2023 study claimed:", False),
            ("", False),
            ("  Rounded corners  ->  +55% click-through rate", False),
            ("", False),
            ("  p-value = 0.037   'Statistically significant!'", False),
            ("", False),
            ("But there was a serious problem.", False),
        ],
    },
    {
        "voiceover": (
            "Statistical power is the probability that your test correctly "
            "detects a real effect when one exists. "
            "The standard target is 80 percent power. "
            "Power depends on three things: your sample size, "
            "the size of the effect you're looking for, "
            "and your significance threshold."
        ),
        "lines": [
            ("WHAT IS STATISTICAL POWER?", True),
            ("", False),
            ("Power = P(detecting a real effect)", False),
            ("", False),
            ("Standard target:  Power >= 80%", False),
            ("", False),
            ("Power depends on:", False),
            ("  * Sample size    (bigger -> more power)", False),
            ("  * Effect size    (bigger -> easier to detect)", False),
            ("  * Alpha level    (alpha = 0.05)", False),
        ],
    },
    {
        "voiceover": (
            "Here is the problem with small studies. "
            "When a study is underpowered, most experiments fail to find anything. "
            "The few that do reach significance are extreme flukes — "
            "statistical outliers that wildly overestimate the true effect. "
            "This is called the Winner's Curse. "
            "The published result is always bigger than reality."
        ),
        "lines": [
            ("THE WINNER'S CURSE", True),
            ("", False),
            ("Small study -> only big flukes look significant", False),
            ("", False),
            ("Published result = a statistical overestimate", False),
            ("", False),
            ("The original study: ~30 participants", False),
            ("", False),
            ("Only extreme noise passed the threshold.", False),
            ("True effect was inflated by roughly 100x.", False),
        ],
    },
    {
        "voiceover": (
            "Researchers then ran five high-powered replications "
            "with over 60,000 users each — more than 2,000 times "
            "the original sample size. "
            "The results told a completely different story. "
            "Effect sizes were about 100 times smaller than claimed, "
            "and none of the replications were statistically significant."
        ),
        "lines": [
            ("THE REPLICATION RESULTS", True),
            ("", False),
            ("Original:       n~30      Effect = +55%    p=0.037", False),
            ("", False),
            ("Replication 1:  n=60,000+   Effect ~ 0.5%   n.s.", False),
            ("Replication 2:  n=60,000+   Effect ~ 0.3%   n.s.", False),
            ("Replication 3:  n=60,000+   Effect ~ 0.6%   n.s.", False),
            ("Evidoo Rep. 1:  n=60,000+   Effect ~ 0.4%   n.s.", False),
            ("", False),
            ("Effect was ~100x smaller than originally claimed.", False),
        ],
    },
    {
        "voiceover": (
            "So what's the lesson? "
            "Before running any experiment, always calculate how many "
            "participants you actually need. "
            "Decide on the smallest effect that would matter to you, "
            "target 80 percent power, and compute your required sample size. "
            "Be skeptical of dramatic results from tiny studies. "
            "And remember — replication is the gold standard of science."
        ),
        "lines": [
            ("KEY TAKEAWAYS", True),
            ("", False),
            ("1. Do power analysis BEFORE the experiment", False),
            ("", False),
            ("2. Define your minimum detectable effect (MDE)", False),
            ("", False),
            ("3. Target Power >= 80%  (more = better)", False),
            ("", False),
            ("4. Be skeptical of big effects from small samples", False),
            ("", False),
            ("5. Replicate before you act on results", False),
        ],
    },
]

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    tmp = tempfile.mkdtemp()
    clips = []

    for i, section in enumerate(SCRIPT):
        label = section["lines"][0][0][:45]
        print(f"[{i+1}/{len(SCRIPT)}] {label} ...")

        # 1. Generate voiceover
        audio_path = os.path.join(tmp, f"vo_{i}.mp3")
        gTTS(section["voiceover"], lang="en", slow=False).save(audio_path)
        audio_clip = AudioFileClip(audio_path)
        duration   = audio_clip.duration + 0.4   # small tail pause

        # 2. Generate frames
        frames = build_frames(section["lines"], duration)

        # 3. Combine
        video = ImageSequenceClip(frames, fps=FPS)
        video = video.with_audio(audio_clip)
        clips.append(video)

    print("\nConcatenating all sections ...")
    final = concatenate_videoclips(clips, method="compose")

    print(f"Writing  ->  {OUTPUT}")
    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    print(f"\nDone!  Video saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
