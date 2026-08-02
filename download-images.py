#!/usr/bin/env python3
"""Downloads every photograph from the Wix CDN into ./images.

Do this BEFORE you cancel Wix. Once the images are local, set
SOURCE = "local" in build.py, re-run build.py, and the site no longer
depends on Wix for anything.

    python3 download-images.py
    # then edit build.py: SOURCE = "local"
    python3 build.py

Requires nothing but Python 3.
"""

import os
import sys
import time
import urllib.request

import photos

PREFIX = "https://static.wixstatic.com/media/7dafb7_"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# Longest edge of the downloaded file. 2400 is plenty for a website and keeps
# pages fast. Raise it if you want bigger, but originals are best kept
# off the web anyway.
MAX_EDGE = 2400

ALL = (
    photos.SHADOW + photos.LIGHT + photos.MONOCHROME
    + photos.BOOK + [photos.PORTRAIT]
)


def main():
    os.makedirs(OUT, exist_ok=True)
    total = len(ALL)
    failed = []

    for i, fname in enumerate(ALL, 1):
        target = os.path.join(OUT, fname.replace("~mv2", ""))
        if os.path.exists(target) and os.path.getsize(target) > 1000:
            print("[%3d/%d] have  %s" % (i, total, os.path.basename(target)))
            continue

        url = "%s%s/v1/fit/w_%d,h_%d,q_90/f.jpg" % (PREFIX, fname, MAX_EDGE, MAX_EDGE)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(target, "wb") as fh:
                fh.write(resp.read())
            print("[%3d/%d] saved %s (%.1f KB)"
                  % (i, total, os.path.basename(target),
                     os.path.getsize(target) / 1024.0))
        except Exception as exc:  # noqa: BLE001
            print("[%3d/%d] FAILED %s -- %s" % (i, total, fname, exc))
            failed.append(fname)
        time.sleep(0.25)

    print("\nDone. %d of %d saved into %s" % (total - len(failed), total, OUT))
    if failed:
        print("These did not download; re-run the script to retry:")
        for f in failed:
            print("  " + f)
        sys.exit(1)
    print('Next: set SOURCE = "local" in build.py, then run python3 build.py')


if __name__ == "__main__":
    main()
