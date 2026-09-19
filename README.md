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
  assets/film/hero/     the homepage clip, one JPEG per frame

build.py              regenerates docs/ from your photo list
photos.py             the photo list — this is the file you edit
captions.py           the title and one-line note under each photograph
shop.py               the print shop: sizes, materials and prices
checkout_server.py    takes the orders — and serves the site while you test
download-images.py    pulls your photographs off Wix onto your machine
film.py               cuts the homepage clip into the frames it scrolls through
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
EMAIL = "maximilien.bozon@gmail.com"   # ← your real address
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

1. Drop the full-size files into `images/` — the masters folder, not `docs/`.
2. Add the filenames to the right list in `photos.py`.
3. Add a title and note in `captions.py` (optional — see below).
4. Run `python3 build.py`.
5. Commit and push — GitHub Pages redeploys on its own.

That's the whole workflow. Order in the list is order on the page.

---

## The homepage film

The homepage opens on a clip that is not played — it is wound by the scroll
wheel. Three screens of scrolling carry it from the first frame to the last,
forwards and backwards, and it stops wherever you stop.

It works by not being a video at all. `film.py` cuts the clip into numbered
stills, and the page keeps one on screen and swaps it for the next as you
scroll. A browser cannot seek inside an H.264 file accurately enough to do
this: the clip carries three keyframes in five seconds, and any seek lands
on one of those three. Separate frames land exactly where they are asked to.

The frames are not taken at a fixed interval. This clip is moving by its
second frame, hits its fastest at the eleventh, then settles — the opening
second moves twenty times as much between frames as the closing one does. So
`film.py` measures every frame against the one before it and keeps one
whenever enough has changed. The pull-back gets all twenty-four frames a
second the clip has; the settled end gets one in six. Each frame records
where in the clip it belongs, in `frames.json`, and the page maps your
scroll position onto those — so the uneven spacing costs nothing and the
timing is unchanged.

To change the clip:

1. Put the new one at `media/scroll-clip.mp4`. That folder is yours alone —
   like `images/`, it is never committed.
2. Run `python3 film.py`. It needs ffmpeg once: `brew install ffmpeg`.
3. Run `python3 build.py`, then commit and push. There is no frame count to
   keep in sync: `build.py` reads `frames.json`.

`FILM_SCREENS` in `build.py` is how many screens of scrolling play the whole
thing — three at the moment. `FILM_EASE`, next to it, decides how evenly
those three screens are spent. At 0 they are spent evenly, and this clip then
rushes its pull-back in the first fifth of the scroll and spends the last
third of it settling almost invisibly. At 0.55, where it is set, the scroll
runs slowly through the opening and quickens towards the end: the pull-back
gets a quarter of the scroll instead of a fifth, and the last third of the
clip takes under a quarter instead of a third. Raising it further starts the
wind at a standstill, which strands the opening — the stretch where this clip
moves fastest. In `film.py`, `THRESHOLD` is how much has to change before a
frame is worth keeping — lower it for more frames and a heavier page — and
`MAX_GAP` is the longest it will go without keeping one.

### How sharp it can be

`WIDTH` in `film.py` is the one number that limits this, and it is set to the
master's own width, because enlarging a frame before saving it adds weight
and no detail. The clip is 1620 pixels wide and a full-screen retina window
asks for around 2880, so the page is still enlarging it by not quite double.
Nothing in the pipeline can recover that. If you can make the clip again at
2880 or wider, do — raise `WIDTH` to match and it is the only change that
puts real detail on the screen. It is not free: the frames are 8.1 MB at
1620 and were 3.4 MB at 1152, so weigh it against the opening screen's load.

The frames are only fetched on a screen wide enough to hold a landscape
picture, and never when the visitor has asked for reduced motion. A phone,
an old browser, or a page with JavaScript switched off gets the still
photograph the homepage always had — which is why that photograph is still
in the markup underneath.

---

## Selling prints

Click a photograph, and the viewer that opens now carries **Order a print**
in its bottom bar. That opens a panel beside the picture: a size, a
material, a framing, a price that adds up as you choose, and a button
through to Stripe's own payment page. The photograph stays on screen the
whole time, because that is the thing being bought.

### The one file you edit

Everything the shop offers and every price it charges lives in `shop.py`,
the same way every photograph lives in `photos.py`. Nothing else in the
project holds a number.

```python
FORMATS = [
    {"id": "40",  "edge": 40,  "paper": 180, "plexi": 260, "frame": 120},
    ...
]
```

`edge` is the **longest side in centimetres**, not a fixed rectangle. Your
photographs are not all the same shape, so a fixed 50×70 would crop a
portrait to fit a frame. Giving the long side and letting the short side
follow means every print is the picture as you made it — and the panel
shows each buyer the real dimensions of the plate in front of them, worked
out from that photograph's own proportions.

Three prices per size, then:

- `paper` — printed on fine art paper
- `plexi` — face-mounted on plexiglass
- `frame` — what the caisse américaine adds, on top of either

`SUPPORTS` and `FRAMINGS` name those options and describe them in one line
each. A framing lists which materials it may be combined with, so a pairing
you don't offer simply cannot be chosen. `SHIPPING` sets the bands Stripe
offers at checkout. `OPEN = False` switches the whole thing off and the
plates go back to being plates.

**The prices in the file now are placeholders.** They are there so the panel
has something to show. Replace them before anyone but you can reach the
site.

### Running it

```bash
export STRIPE_SECRET_KEY=sk_test_...
python3 checkout_server.py
```

Then open <http://localhost:8000> and order something. The key comes from
your Stripe dashboard — start with the **test** key, `sk_test_...`, and pay
with card number `4242 4242 4242 4242`, any future expiry, any CVC. No money
moves. The server prints which mode it is in when it starts, so you always
know whether a card would really be charged.

One process does two jobs: it serves `docs/` exactly as a static host would,
and it answers `POST /api/checkout` on the same address. Same origin, so
there is no CORS to configure, and what you test locally is what runs later.
It uses nothing but the standard library — no `pip install`, no dependency
to keep current.

### What the browser is trusted with

Which photograph, which size, which material, which framing. That is all.

**The price is never sent by the browser.** It is looked up again in
`shop.py`, on the server, every single time, and that is the number Stripe
charges. A page that could name its own price would be a page anyone could
edit — the developer tools are right there. The photograph's title and
series are looked up server-side too, from `captions.py`, so an order can't
claim to be for something it isn't.

Each payment carries the plate, series, size, material, framing and
filename in its metadata, so an order can be filled from the Stripe
dashboard without opening anything else.

### Putting it online

The site itself is static and GitHub Pages serves it happily. The checkout
endpoint is not static — it needs somewhere to run, because creating a
payment requires a secret key and a secret key cannot live in a web page.

The smallest honest options:

| Where | What it costs | What you do |
| --- | --- | --- |
| **Cloudflare Workers** | free at this volume | port `_checkout` to a Worker, point `CHECKOUT_ENDPOINT` at it |
| **A small VPS** | ~€5/month | run `checkout_server.py` behind nginx |
| **Stripe Payment Links** | free, no server | see below |

If you'd rather not run anything at all, Stripe **Payment Links** are the
way: make one link per size-and-material combination in the dashboard and
have the panel send people to the matching link. You lose the per-photograph
line on the receipt — the payment records which plate it was, but the buyer
sees a generic product name — and every price change becomes dashboard work
instead of one line in `shop.py`. That is the trade.

Whichever you choose, set `PUBLIC_IMAGE_BASE=https://maximilienbozon.com`
so Stripe can fetch the photograph and show it on the payment page. It can't
do that from your laptop, which is why the picture is missing locally.

### Before taking real money

- Replace the placeholder prices, and check the total on screen against what
  Stripe actually charges.
- Fill in `SHIPPING` properly — a print at 100 cm is not posted for the same
  as one at 40.
- Swap `sk_test_` for `sk_live_` only at the very end, and order one print
  from yourself before telling anyone.
- Selling to consumers in the EU comes with obligations this code knows
  nothing about: a right of withdrawal, terms of sale, and VAT once you pass
  the threshold. Stripe Tax can handle the VAT; the rest is a page of text
  you'll want to write.

---

## About people taking your photographs

Read this part honestly, because the internet is full of products that sell
you the opposite.

**You cannot stop someone downloading a photograph you display.** To draw a
picture on screen, the browser must first be given the picture. At that point
it is on their machine, and no script can take it back. Disabled right-click,
transparent overlays, canvas tricks, "encrypted" images — all of it is undone
by the network panel, or by pressing the screenshot key. Anyone selling you
image protection is selling you a feeling.

What you *can* decide is how good a copy a thief walks away with. That is a
real choice, and this is what the build does about it:

- **Your masters never leave your machine.** `images/` holds the full-size
  files and is excluded from git. Nothing in it is ever published.
- **The site serves 2000px copies**, made by `build.py`. The widest plate in
  the layout is about 1216 CSS pixels, so this is already more than the page
  can show — you lose nothing on screen. But it caps a print at roughly 17cm
  instead of the 20cm a 2400px file would give away.
- **Every published file carries a copyright field** in its metadata, which
  survives being saved and re-uploaded and is useful if you ever have to make
  a claim.
- **Right-click and drag are disabled on the photographs**, and on those only
  — right-click still works normally on text and links. This stops the
  opportunist who would have saved it without thinking. It stops nobody else,
  and it is not meant to.

To change the cap, edit `MAX_EDGE` in `build.py` and re-run it; every copy is
regenerated automatically when that number changes.

The measure that actually protects your work is not technical. It is that
your name is on the site, the files carry your copyright, and the version in
circulation is too small to print well.

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
