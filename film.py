#!/usr/bin/env python3
"""Cuts a video into the still frames the homepage scrolls through.

The hero clip is not played. It is scrubbed: the page holds one frame on
screen and swaps it for the next as you scroll, so the scroll wheel becomes
the transport. That needs the frames as separate files, because a browser
cannot seek inside an H.264 file accurately enough to do it — this clip
carries three keyframes in five seconds, and seeking lands on those.

Frames are not taken at a fixed interval. This clip is moving by its second
frame, hits its fastest at the eleventh, then settles: the opening second
moves twenty times as much between frames as the closing one does. Sampling
evenly would spend half the download on frames nobody can tell apart. So
every frame is measured against the one before it, and a frame is kept
whenever enough has changed since the last one kept. Motion gets all the
frames the clip has; stillness gets a handful. Each kept frame records
where in the clip it belongs, so the timing of the piece is unchanged —
only the spacing of the stills that describe it.

    python3 film.py

Reads ./media/scroll-clip.mp4 and writes docs/assets/film/hero/001.jpg ...
alongside frames.json, which build.py reads. Requires ffmpeg (brew install
ffmpeg). The frames are committed; the master clip in ./media is not, the
same arrangement as ./images and docs/images.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "media", "scroll-clip.mp4")
OUT = os.path.join(HERE, "docs", "assets", "film", "hero")

# Frame width in pixels, set to the master's own width — asking for more
# would only enlarge it, which adds weight and no detail, and the page can
# enlarge it for free. This is the one number that limits how sharp the hero
# can be: a higher-resolution master raises it, nothing else does. Even at
# 1620 a full-screen retina window asks for around 2880, so the page is
# still enlarging it by not quite double, and a wider master would still buy
# real detail.
WIDTH = 1620

# JPEG quality, ffmpeg's scale: 2 is near-lossless and enormous, 31 is a
# mess. 4 measures 43.0dB against the source, which is past the point of
# seeing the difference, and leaves headroom in the smooth dark greys of the
# wall, where banding would show long before blockiness did.
QUALITY = 4

# How much has to change before a frame is worth keeping. Mean absolute
# difference per pixel, measured on a 64-wide grey copy — about 1.6 is the
# point where two frames stop being tellable apart in motion.
THRESHOLD = 1.6

# Never leave more than this many of the clip's own frames between two kept
# ones, however still it goes. At 24fps this is a third of a second, and it
# only ever applies where nothing is moving.
MAX_GAP = 8


def main():
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found. Install it with:  brew install ffmpeg")
    if not os.path.isfile(SOURCE):
        sys.exit("No clip at %s" % SOURCE)

    keep, total = choose()

    # Start clean, or a shorter clip would leave the tail of a longer one
    # behind and the page would scroll into frames from the old film.
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    extract(keep)

    # Where each kept frame sits in the clip, 0 to 1. The page maps how far
    # you have scrolled onto these, so uneven spacing costs nothing.
    times = [round(n / float(total - 1), 6) for n in keep]
    with open(os.path.join(OUT, "frames.json"), "w", encoding="utf-8") as fh:
        json.dump({"width": WIDTH, "times": times}, fh)
        fh.write("\n")

    weight = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    gaps = [keep[i] - keep[i - 1] for i in range(1, len(keep))]
    print("Kept %d of %d frames (%.1f MB) in %s"
          % (len(keep), total, weight / 1e6, os.path.relpath(OUT, HERE)))
    print("Closest spacing %d frame, widest %d — the widest is where the "
          "picture is still." % (min(gaps), max(gaps)))
    print("build.py reads frames.json, so there is no count to update.")


def choose():
    """Measure every frame against the one before it and pick the keepers.

    The measuring is done on a 64-pixel-wide greyscale copy of the clip.
    That is small enough to compare in plain Python and large enough that
    nothing meaningful moves without showing up in it.
    """
    wide, high = 64, 43
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", SOURCE,
         "-vf", "scale=%d:-1,format=gray" % wide, "-f", "rawvideo", "-"],
        check=True, stdout=subprocess.PIPE).stdout

    size = wide * high
    total = len(raw) // size
    if total < 2:
        sys.exit("Could not read frames from %s" % SOURCE)

    frames = [raw[i * size:(i + 1) * size] for i in range(total)]

    keep = [0]
    change = 0.0
    for i in range(1, total):
        change += sum(abs(a - b) for a, b in zip(frames[i], frames[i - 1])) / size
        if change >= THRESHOLD or i - keep[-1] >= MAX_GAP:
            keep.append(i)
            change = 0.0
    if keep[-1] != total - 1:
        keep.append(total - 1)

    return keep, total


def extract(keep):
    """Write out the chosen frames, renumbered from 001.

    ffmpeg writes all of them into a scratch folder first. Asking it for a
    list of frame numbers means building a select expression with one term
    per frame, and this is both shorter to read and easier to trust.
    """
    scratch = tempfile.mkdtemp(prefix="film-")
    try:
        subprocess.run([
            "ffmpeg", "-v", "error", "-i", SOURCE,
            "-vf", "scale=%d:-2" % WIDTH,
            "-fps_mode", "passthrough",
            "-q:v", str(QUALITY),
            "-y", os.path.join(scratch, "%04d.jpg"),
        ], check=True)

        for out, n in enumerate(keep, start=1):
            shutil.move(os.path.join(scratch, "%04d.jpg" % (n + 1)),
                        os.path.join(OUT, "%03d.jpg" % out))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
