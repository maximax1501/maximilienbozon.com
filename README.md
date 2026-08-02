# maximilienbozon.com — static rebuild

A hand-built replacement for the Wix site. No subscription, no page builder,
no database. Just files.

Everything from the old site is here: **Shadow** (36), **Light** (24),
**Monochrome** (16), the **Notice it** edition, **About** and **Contact**.

---

## What's in the box

```
docs/                 ← this is the website. GitHub Pages serves this folder.
  index.html
  shadow.html  light.html  monochrome.html
  notice-it.html  about.html  contact.html  404.html
  sitemap.xml  robots.txt
  assets/css/site.css
  assets/js/site.js

build.py              regenerates docs/ from your photo list
photos.py             the photo list — this is the file you edit
captions.py           the title and one-line note under each photograph
download-images.py    pulls your photographs off Wix onto your machine
```

You can open `docs/index.html` in a browser right now to see it.

---

## Do this in order

### 1. Look at it

Open `docs/index.html`. Right now the photographs are still being served from
Wix's image CDN, which is why it works instantly.

### 2. Get your photographs off Wix — before you cancel

```bash
python3 download-images.py     # saves everything into ./images
```

Then open `build.py`, change one line near the top:

```python
SOURCE = "local"
```

and run:

```bash
python3 build.py
```

Now copy the `images/` folder into `docs/`. The site no longer touches Wix.
**Don't cancel the Wix plan until this step is finished** — the download
script reads from their CDN.

Also worth doing: export your originals from Wix's media manager directly
(Site & App → Media), since the download script fetches web-sized copies
capped at 2400px, not your full-resolution files.

### 3. Put your email address in

Two places in `build.py`, near the top:

```python
EMAIL = "contact@maximilienbozon.com"   # ← your real address
```

I couldn't find an address on the old site, so this is a placeholder.
Change it and re-run `python3 build.py`.

The contact form works with no back end at all — it opens the visitor's mail
app with the message prefilled. If you'd rather have submissions land in your
inbox automatically, make a free endpoint at
[formspree.io](https://formspree.io) or [formsubmit.co](https://formsubmit.co)
and paste it into the form's `action=""` in `build.py`.

### 4. Host it

All of these are free for a site this size, and all of them let you point
`maximilienbozon.com` at them:

| Host | How |
| --- | --- |
| **Cloudflare Pages** | Drag the `docs` folder onto the dashboard. Free custom domain, free SSL. |
| **Netlify** | Same — drag and drop at app.netlify.com/drop. |
| **GitHub Pages** | ← this is what the site uses now. See below. |

This site is on **GitHub Pages**, serving the `docs/` folder of
`maximax1501/maximilienbozon.com` on the `main` branch. Pages will only serve
the repository root or a folder named `docs/`, which is why the built site
lives under that name.

To publish a change: run `python3 build.py`, then commit and push. That's it.

The `docs/CNAME` file holds the custom domain and is written by `build.py`,
so rebuilding can never knock the domain off the site.

Whichever you choose, add `maximilienbozon.com` as a custom domain in their
dashboard and follow their DNS instructions.

### 5. Move the domain

Your domain may currently be registered *through* Wix. Two options:

- **Transfer it out** to a registrar like Cloudflare, Namecheap or Gandi
  (roughly €10–15/year, versus Wix's bundled price). You'll need to unlock the
  domain in Wix and request the authorisation code first.
- **Or keep it registered at Wix** and just repoint the DNS records at your new
  host. Cheaper in effort, but you stay a Wix customer for the domain.

Cancel the Wix *premium plan* only once the new site is live and the domain
resolves to it.

---

## Adding photographs later

1. Drop the image files into `docs/images/`.
2. Add the filenames to the right list in `photos.py`.
3. Add a title and note in `captions.py` (optional — see below).
4. Run `python3 build.py`.
5. Commit and push — GitHub Pages redeploys on its own.

That's the whole workflow. Order in the list is order on the page.

---

## The titles and notes

Every plate carries a title and one sentence, and they live in `captions.py`:

```python
SHADOW = {
    "852e5a": ("Plumage Unfolded",
               "A greater flamingo turns to preen and the raised wing opens like a fan of coral and white."),
```

The key is the first six characters of the filename, so reordering a series
never detaches a caption from its photograph. **I wrote these from looking at
the pictures — they are a starting point, not gospel.** You know what you shot
and where; rewrite anything that's wrong or that you'd phrase differently, then
re-run `python3 build.py`.

Two things worth knowing:

- A photograph with no entry still builds. It just shows its number and series,
  as before.
- The caption is also the image's alt text, so it's what a screen reader and
  Google both read. That's another reason to make it accurate.

Keep titles to a few words and notes to one sentence — the layout is built
around that length.

---

## Notes on the design

- **Bodoni Moda** for display — the didone cut used in nineteenth-century
  natural-history atlases and anatomical plates, which felt right for a
  veterinarian photographing anatomy. **Spectral** for reading, **Archivo**
  for specimen-tag labels.
- **No accent colour.** The only warm tone in the palette is the light itself.
  On a body of work about darkness, a coloured accent would be noise.
- **The overture.** The home page opens on a black panel that draws the name
  out of the dark and then lifts like a curtain. It runs once per visit, gets
  out of the way after about three seconds, and skips the moment you click,
  scroll or touch anything. Come back to the home page later in the same
  session and it doesn't replay.
- **Expanding a plate.** Hovering a photograph offers *Expand*; clicking gives
  it the whole screen with its title and note underneath, and arrow keys or the
  side buttons walk through the series. Escape closes it. On a phone, where
  there's no hover to wait for, the control is simply always there — and with
  JavaScript off it's an ordinary link straight to the full-size file.
- **The lamp.** A single soft light source follows the cursor across the black
  page, and each photograph lifts from dim to full brightness as it reaches the
  middle of the screen — the pictures are literally revealed by a moving light.
  It's the one bold move; everything else stays quiet.
- **Plates, not a grid.** Photographs are presented one at a time down a single
  column at varying widths, numbered in roman numerals like plates in a
  portfolio — echoing the hand-numbered *Notice it* edition. A dense thumbnail
  grid would fight work that depends on scale and darkness.
- Works on a phone, keyboard-navigable with visible focus, honours
  "reduce motion", and stays readable if JavaScript never loads.
