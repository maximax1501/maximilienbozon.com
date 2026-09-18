#!/usr/bin/env python3
"""The print shop's back end, and a local web server to try it with.

    export STRIPE_SECRET_KEY=sk_test_...
    python3 checkout_server.py

Then open http://localhost:8000, click a photograph, and order a print.

It does two jobs from one process, which is the point: it serves ./docs
exactly as a static host would, and it answers POST /api/checkout on the
same origin, so the page never makes a cross-origin request and there is no
CORS to configure. What you test locally is what runs later.

Only the standard library is used — no pip install, no dependency to keep
up to date. Stripe's API is a form-encoded POST with a bearer token, which
urllib does perfectly well.

WHAT THE BROWSER IS TRUSTED WITH: which photograph, which size, which
print, which framing. Nothing else. The price is looked up here, in
shop.py, every single time. A browser that asks for a 100 cm plexiglass
print at four euros gets one at the real price, because the number it sent
is never read.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import captions
import photos
import shop

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")

PORT = int(os.environ.get("PORT", "8000"))
# Loopback locally, every interface in a container. Railway routes to the
# process from outside the machine, so a server listening only on 127.0.0.1
# there is a server nobody can reach.
HOST = os.environ.get("HOST", "127.0.0.1")
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_API = "https://api.stripe.com/v1/checkout/sessions"

# Where the SITE lives, when that is not where this process lives.
#
# Locally the two are the same thing and this stays empty: one process
# serves docs/ and answers /api/checkout, and the origin off the request is
# the right answer for everything. In production they are split — the
# photographs are on GitHub Pages at maximilienbozon.com, this is on
# Railway — and the request origin is then this API host, which is the one
# host the buyer must never be sent back to. Stripe would return them to
# an API box with no order-complete page on it.
#
# So: set this to the site, and every address handed to Stripe or allowed
# through CORS is built from it rather than from the request.
#
#     SITE_ORIGIN=https://maximilienbozon.com
SITE_ORIGIN = os.environ.get("SITE_ORIGIN", "").rstrip("/")

# Stripe will only show a picture in its checkout if it can fetch the file
# itself, which it cannot do from your laptop. Set this to the live site
# once the shop is published and the buyer sees the photograph they chose
# on the payment page; leave it unset locally and they simply do not.
#
#     export PUBLIC_IMAGE_BASE=https://maximilienbozon.com
PUBLIC_IMAGE_BASE = os.environ.get("PUBLIC_IMAGE_BASE", "").rstrip("/") \
    or SITE_ORIGIN


# ------------------------------------------------------------- the plates
#
# Which photographs exist, and what each one is called, is settled here
# rather than taken from the request. The browser sends a six-character id
# and nothing it says about the picture is believed.

def _catalogue():
    out = {}
    for files, series, caps in (
        (photos.SHADOW, "Shadow", captions.SHADOW),
        (photos.LIGHT, "Light", captions.LIGHT),
        (photos.MONOCHROME, "Monochrome", captions.MONOCHROME),
    ):
        for i, fname in enumerate(files):
            key = fname[:6]
            if key in out:
                continue
            title, _brief = caps.get(key, ("", ""))
            out[key] = {
                "title": title or "Untitled",
                "series": series,
                "plate": i + 1,
                "file": fname.replace("~mv2", ""),
            }
    return out


CATALOGUE = _catalogue()

ID_RE = re.compile(r"^[0-9a-f]{6}$")


# --------------------------------------------------------------- stripe

def _form(pairs):
    """Stripe takes nested data as bracketed form keys, not JSON."""
    return urllib.parse.urlencode(pairs).encode("utf-8")


def _flatten(prefix, value, out):
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten("%s[%s]" % (prefix, k) if prefix else k, v, out)
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _flatten("%s[%d]" % (prefix, i), v, out)
    elif value is not None:
        out.append((prefix, str(value)))
    return out


def stripe_session(params):
    req = urllib.request.Request(
        STRIPE_API,
        data=_form(_flatten("", params, [])),
        headers={
            "Authorization": "Bearer " + STRIPE_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            # Stripe records the integration that made the call; naming it
            # makes a support conversation about this shop much shorter.
            "Stripe-Version": "2023-10-16",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def shipping_options(sid, gid):
    """Every shipping band from shop.py, priced for this order.

    Most of what the shop sells carries its transport in the print price,
    so the band is offered at zero and Stripe shows the buyer the word
    rather than a sum. The bare paper print pays the band outright. Which
    is which is shop.carriage's answer, not this file's, so the panel and
    the bill are reading the same rule."""
    out = []
    for band in shop.SHIPPING[:5]:          # Stripe accepts at most five
        due = shop.carriage(sid, gid, band)
        out.append({
            "shipping_rate_data": {
                "type": "fixed_amount",
                "display_name": band["label"] if due else
                                "%s — shipping included" % band["label"],
                "fixed_amount": {
                    "amount": shop.cents(due),
                    "currency": shop.CURRENCY,
                },
            }
        })
    return out


def allowed_countries():
    seen = []
    for band in shop.SHIPPING:
        for c in band["countries"]:
            if c not in seen:
                seen.append(c)
    return seen


# --------------------------------------------------------------- handler

class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DOCS, **kw)

    def log_message(self, fmt, *args):
        # The static traffic is noise; only the orders are worth a line.
        if self.path.startswith("/api/"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- the one endpoint

    def do_POST(self):
        if self.path.rstrip("/") != "/api/checkout":
            return self.send_error(404, "No such endpoint")
        try:
            self._checkout()
        except Exception as exc:                       # never leak a stack
            sys.stderr.write("checkout failed: %r\n" % (exc,))
            self._json(500, {"error": "The shop could not reach Stripe."})

    def _checkout(self):
        if not STRIPE_KEY:
            return self._json(503, {
                "error": "The shop is not connected to Stripe yet."})

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 8192:
            return self._json(400, {"error": "Malformed order."})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return self._json(400, {"error": "Malformed order."})

        photo = str(body.get("photo", ""))
        if not ID_RE.match(photo) or photo not in CATALOGUE:
            return self._json(400, {"error": "That photograph is not for sale."})
        plate = CATALOGUE[photo]

        fid = str(body.get("format", ""))
        sid = str(body.get("support", ""))
        gid = str(body.get("framing", ""))

        # The only number that matters, and it comes from shop.py.
        euros = shop.price(fid, sid, gid)
        line = shop.describe(fid, sid, gid)
        if euros is None or line is None:
            return self._json(400, {"error": "That combination is not offered."})
        if euros <= 0:
            return self._json(503, {
                "error": "That print has no price set yet."})

        site = self._site()
        product = {
            "name": "%s — %s, plate %s" % (plate["title"], plate["series"],
                                           _roman(plate["plate"])),
            "description": line,
        }
        if PUBLIC_IMAGE_BASE:
            product["images"] = [PUBLIC_IMAGE_BASE + "/images/" + plate["file"]]

        params = {
            "mode": "payment",
            "success_url": site + "/order-complete.html?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": self._cancel(body, site),
            "client_reference_id": photo,
            "line_items": [{
                "quantity": 1,
                "price_data": {
                    "currency": shop.CURRENCY,
                    "unit_amount": shop.cents(euros),
                    "product_data": product,
                },
            }],
            "shipping_address_collection": {
                "allowed_countries": allowed_countries(),
            },
            "shipping_options": shipping_options(sid, gid),
            "phone_number_collection": {"enabled": "false"},
            # Everything needed to make the print, on the payment itself,
            # so an order can be filled from the Stripe dashboard alone.
            "metadata": {
                "photo": photo,
                "title": plate["title"],
                "series": plate["series"],
                "plate": _roman(plate["plate"]),
                "format": fid,
                "support": sid,
                "framing": gid,
                "file": plate["file"],
            },
        }

        try:
            session = stripe_session(params)
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")
            sys.stderr.write("stripe rejected the order: %s\n" % detail)
            return self._json(502, {"error": "Stripe refused the order."})

        sys.stderr.write("order %s — %s, %s, %s%s\n" % (
            session.get("id", "?"), plate["title"], line, shop.SYMBOL, euros))
        return self._json(200, {"url": session.get("url")})

    # ---- plumbing

    def _origin(self):
        host = self.headers.get("Host") or ("localhost:%d" % PORT)
        scheme = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
        return "%s://%s" % (scheme, host)

    def _site(self):
        """Where the buyer came from and must be returned to. SITE_ORIGIN
        when the site is hosted apart from this process, and the request's
        own origin when it is not."""
        return SITE_ORIGIN or self._origin()

    def _allow_origin(self):
        """The one origin permitted to call this endpoint from a browser.

        Deliberately a single exact origin rather than '*': this endpoint
        creates priced Stripe sessions, and there is no reason for any page
        but the shop to be able to open one. Empty when SITE_ORIGIN is
        unset, which is the same-origin local case where no CORS header
        should be sent at all."""
        return SITE_ORIGIN

    def _cors(self):
        allow = self._allow_origin()
        if not allow:
            return
        if self.headers.get("Origin") != allow:
            return
        self.send_header("Access-Control-Allow-Origin", allow)
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        """The preflight the browser sends before the real POST, because
        the order is JSON and therefore never a 'simple' request."""
        if self.path.rstrip("/") != "/api/checkout":
            return self.send_error(404, "No such endpoint")
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _cancel(self, body, site):
        """Send a buyer who backs out to the photograph they were looking
        at, not to the front door.

        The address is checked against the site before it is used. It
        arrives in the request body, so an unchecked returnTo would let
        anyone hand Stripe an address on a host of their choosing and have
        the shop's own checkout page send a buyer there."""
        want = str(body.get("returnTo", ""))
        parsed = urllib.parse.urlparse(want)
        if parsed.scheme in ("http", "https") and \
                "%s://%s" % (parsed.scheme, parsed.netloc) == site:
            return want
        return site + "/"

    def _json(self, code, payload):
        blob = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)


_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
          (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
          (5, "V"), (4, "IV"), (1, "I")]


def _roman(n):
    out = ""
    for value, sym in _ROMAN:
        while n >= value:
            out += sym
            n -= value
    return out


def main():
    if not os.path.isdir(DOCS) and not SITE_ORIGIN:
        sys.exit("docs/ is missing — run python3 build.py first.")

    mode = "not connected"
    if STRIPE_KEY.startswith("sk_test_"):
        mode = "TEST mode — no real money moves"
    elif STRIPE_KEY.startswith("sk_live_"):
        mode = "LIVE mode — real cards will be charged"
    elif STRIPE_KEY:
        mode = "key present but unrecognised"

    print("maximilienbozon.com — http://%s:%d" % (HOST, PORT))
    print("Stripe: %s" % mode)
    print("Site:   %s" % (SITE_ORIGIN or "same origin as this process"))
    print("Catalogue: %d photographs, %d formats" % (len(CATALOGUE), len(shop.FORMATS)))
    if not STRIPE_KEY:
        print("\n  Set a key first:  export STRIPE_SECRET_KEY=sk_test_...")
    print("\nCtrl-C to stop.\n")

    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
