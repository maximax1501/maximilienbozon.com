#!/usr/bin/env python3
"""Cuts a video into the still frames the homepage scrolls through.

The hero clip is not played. It is scrubbed: the page holds one frame on
screen and swaps it for the next as you scroll, so the scroll wheel becomes
the transport. That needs the frames as separate files, because a browser
cannot seek inside an H.264 file accurately enough to do it — this clip
carries three keyframes in five seconds, and seeking lands on those.

Every frame the clip has is kept, evenly spaced. An earlier version measured
each frame against the one before it and dropped the ones that had barely
changed, on the reasoning that nobody could tell them apart. That saved a
third of the weight and cost more than it saved: the frames it dropped were
the ones the picture was moving slowly through, which is exactly where the
eye has time to notice a step. And motion that was never cut cannot be put
back by the page — no amount of smoothing invents a frame that is not there.
So the film is the clip, frame for frame, and the page's smoothing has
something continuous to work on.

The same frames are cut twice, at two widths. The wide set is for screens
with room to be filled by a landscape picture. The narrow set, in hero/sm,
is for phones, which never fill their window with this clip and should not
be asked for eleven megabytes to prove it.

    python3 film.py

Reads ./media/scroll-clip.mp4 and writes docs/assets/film/hero/001.jpg ...
and hero/sm/001.jpg ..., alongside frames.json, which build.py reads.
Requires ffmpeg (brew install ffmpeg). The frames are committed; the master
clip in ./media is not, the same arrangement as ./images and docs/images.
"""

import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "assets", "film", "hero")

# The master, whatever container it came out of — .mp4, .mov, anything
# ffmpeg opens. Found rather than named, so that re-exporting the clip is
# the whole of the job: drop it in as media/scroll-clip.<something> and run
# this. Exactly one is expected, and two is an error rather than a guess,
# because guessing wrong here is a film nobody asked for on the homepage.
CLIPS = sorted(glob.glob(os.path.join(HERE, "media", "scroll-clip.*")))
SOURCE = CLIPS[0] if len(CLIPS) == 1 else ""

# Frame width in pixels. None means the master's own width, which is almost
# always the right answer: asking for more would only enlarge the frames
# before saving them, which adds weight and no detail, and the page can
# enlarge them for free. Put a number here only to cut deliberately smaller
# than the master.
#
# This is the one number that limits how sharp the hero can be, and the only
# thing that raises it is a better master — so it is read off the master
# rather than kept here to be updated and forgotten. Re-export the clip
# larger, run this, and the film is sharper. There is nothing else to
# change.
WIDTH = None

# But not past this. The frames are enlarged by the page to fill the window,
# and how much depends on its shape: a full-screen retina window asks for
# around 2880 across, and a window taller than the frame is 3:2 asks the
# frame's 2:3-worth of height to cover its own, which wants the same again.
# Past 2880 the film is carrying detail no screen is asking for, and every
# byte of it is on the opening screen of the homepage.
MAX_WIDTH = 2880

# Past this the film is too heavy to put on an opening screen, whatever it
# looks like. Not enforced — the master is yours and so is the call — but
# said out loud, because the way to find out otherwise is to publish it.
BUDGET_MB = 16

# JPEG quality, ffmpeg's scale: 2 is near-lossless and enormous, 31 is a
# mess. 4 measures 43.0dB against the source, which is past the point of
# seeing the difference, and leaves headroom in the smooth dark greys of the
# wall, where banding would show long before blockiness did. This is the
# knob to turn if the whole film has to weigh less: every frame is now kept,
# so the only thing left to trade is how each one is written.
QUALITY = 4

# The same film, cut for a phone.
#
# A phone cannot be filled by this clip. Cropping a landscape frame to an
# upright window keeps only the middle third of its width, and the middle
# third is not where this clip ends up — it ends on a framed print whose own
# edges are near the left and right of the frame, and cropping cuts them
# off. So on a phone the page fits the picture to the width instead and
# lets the dark take the rest of the window, which means it never draws the
# picture wider than the phone is, plus whatever the opening zoom asks for.
#
# A phone draws the film at the width of its screen less the gutters, which
# is about 780 pixels on the commonest phone and 860 on the widest made.
# 810 covers the first exactly and the second within a rounding error, and
# it is the smallest number that does — which matters, because this is the
# cut that travels on somebody's data plan.
#
# 5 rather than 4 because these frames are shown smaller, where quality
# costs less and megabytes cost more.
SMALL = "sm"
SMALL_WIDTH = 810
SMALL_QUALITY = 5


def master_width():
    """How wide the clip actually is, asked of it rather than remembered."""
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width", "-of", "csv=p=0", SOURCE,
    ], capture_output=True, text=True)
    try:
        return int(probe.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        sys.exit("ffprobe found no video in %s\n%s"
                 % (SOURCE, probe.stderr.strip() or probe.stdout.strip()))


def cut(out, width, quality):
    """One pass of ffmpeg: every frame of the clip, at one width."""
    os.makedirs(out)

    # passthrough, so ffmpeg writes the frames the clip actually has rather
    # than resampling them to some rate of its own choosing. %03d numbers
    # them from 001, which is what the page asks for.
    subprocess.run([
        "ffmpeg", "-v", "error", "-i", SOURCE,
        "-vf", "scale=%d:-2" % width,
        "-fps_mode", "passthrough",
        "-q:v", str(quality),
        "-y", os.path.join(out, "%03d.jpg"),
    ], check=True)

    frames = sorted(f for f in os.listdir(out) if f.endswith(".jpg"))
    if len(frames) < 2:
        sys.exit("ffmpeg wrote %d frames from %s" % (len(frames), SOURCE))
    weight = sum(os.path.getsize(os.path.join(out, f)) for f in frames)
    return frames, weight


def main():
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        sys.exit("ffmpeg not found. Install it with:  brew install ffmpeg")
    if not CLIPS:
        sys.exit("No clip at media/scroll-clip.* — put the master there.")
    if len(CLIPS) > 1:
        sys.exit("More than one master in media/, and no way to choose:\n  %s"
                 % "\n  ".join(os.path.relpath(c, HERE) for c in CLIPS))

    master = master_width()
    width = WIDTH or master
    if width > MAX_WIDTH:
        width = MAX_WIDTH
    width -= width % 2          # ffmpeg's scale wants an even width

    # The narrow cut is sized to phones, not to the master, so it does not
    # move when the master does — unless the master is smaller than it is,
    # in which case enlarging to reach 900 would be weight for nothing.
    small_width = min(SMALL_WIDTH, width)

    # Start clean, or a shorter clip would leave the tail of a longer one
    # behind and the page would scroll into frames from the old film.
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)

    frames, weight = cut(OUT, width, QUALITY)
    small, small_weight = cut(os.path.join(OUT, SMALL), small_width, SMALL_QUALITY)

    # Both sets are the same frames at two sizes, and the page swaps between
    # them by the screen it is on. If they ever came out different lengths
    # the page would ask the narrow set for a frame it does not have, so
    # that is checked here rather than discovered on a phone.
    if len(small) != len(frames):
        sys.exit("The two cuts disagree: %d wide frames, %d narrow"
                 % (len(frames), len(small)))

    # Where each frame sits in the clip, 0 to 1. Even spacing, because the
    # frames are the clip's own and arrive at its own rate. The page reads
    # this rather than counting files, so an uneven film would still work —
    # nothing downstream assumes the spacing.
    times = [round(i / float(len(frames) - 1), 6) for i in range(len(frames))]
    with open(os.path.join(OUT, "frames.json"), "w", encoding="utf-8") as fh:
        json.dump({"width": width, "small": small_width,
                   "smallPath": SMALL + "/", "times": times}, fh)
        fh.write("\n")

    print("Kept all %d frames in %s" % (len(frames), os.path.relpath(OUT, HERE)))
    print("  %4d px wide: %5.1f MB   (screens with room for it)" % (width, weight / 1e6))
    print("  %4d px wide: %5.1f MB   (%s/, phones)"
          % (small_width, small_weight / 1e6, SMALL))
    print("build.py reads frames.json, so there is no count to update.")

    if width < master:
        print("\nThe master is %d px wide and the film was cut at %d."
              % (master, width))
        print("Raise MAX_WIDTH if you want the rest of it." if not WIDTH
              else "WIDTH is set; clear it to follow the master.")
    if weight / 1e6 > BUDGET_MB:
        print("\nThat wide cut is %.1f MB on the homepage's opening screen,"
              " over the %d MB this file calls too much." % (weight / 1e6, BUDGET_MB))
        print("QUALITY is at %d; raising it is the knob that costs least —"
              " every frame is kept either way." % QUALITY)


if __name__ == "__main__":
    main()
