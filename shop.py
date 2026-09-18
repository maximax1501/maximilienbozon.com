# The print shop — this is the file you edit.
#
# Everything the order panel offers, and every price it charges, is here.
# Nothing else in the project holds a number: build.py renders this into the
# pages and checkout_server.py charges from it, so the two can never
# disagree about what a print costs.
#
# Prices are in euros, as you would write them on a price list. They are
# converted to cents once, in cents(), so nobody has to think in cents.

CURRENCY = "eur"
SYMBOL = "€"

# Where an enquiry goes when the shop is switched off, or when a visitor
# would rather ask than buy.
ENQUIRY_EMAIL = "maximilien.bozon@gmail.com"

# The address checkout_server.py answers on. Left relative so the same build
# works on localhost now and behind a real domain later.
CHECKOUT_ENDPOINT = "/api/checkout"

# Set False to build the site with no ordering at all — the plates go back
# to being just plates, and no order button is rendered anywhere.
#
# It is False because the published site has nowhere to send an order:
# CHECKOUT_ENDPOINT is answered by checkout_server.py, and GitHub Pages
# serves files and nothing else. Switch it on once that server is hosted
# somewhere and re-run build.py.
OPEN = False


# ---------------------------------------------------------------- formats
#
# A format is a longest edge in centimetres, not a fixed rectangle. The
# photographs here are not all the same shape, so a 50x70 that fits a
# panorama would crop a portrait. Giving the long side and letting the
# short side follow the photograph means every print is the picture you
# actually looked at, uncropped — and the panel shows the buyer the real
# dimensions of the plate in front of them.
#
#   id     used in the payment record; keep it stable once you have sold one
#   edge   longest side, in centimetres
#   paper  price on fine art paper
#   plexi  price face-mounted on plexiglass
#   frame  supplement for the caisse americaine at this size
#
# >>> THE NUMBERS BELOW ARE PLACEHOLDERS. Replace them before the shop
# >>> is ever reachable by a stranger. They are here only so the panel has
# >>> something to show while you look at it.
FORMATS = [
    {"id": "40",  "edge": 40,  "paper": 180, "plexi": 260, "frame": 120},
    {"id": "60",  "edge": 60,  "paper": 280, "plexi": 390, "frame": 170},
    {"id": "80",  "edge": 80,  "paper": 420, "plexi": 560, "frame": 230},
    {"id": "100", "edge": 100, "paper": 590, "plexi": 780, "frame": 300},
]

# ---------------------------------------------------------------- supports
#
# How the photograph is printed. The note is the one line shown under the
# name in the panel — say what the material does to the picture, not what
# the process is called.
#
SUPPORTS = [
    {"id": "paper", "label": "Fine art paper",
     "note": "Hahnemühle cotton rag, pigment inks. Matte, deep blacks, no reflection."},
    {"id": "plexi", "label": "Plexiglass",
     "note": "Face-mounted under acrylic. Glossy, luminous, holds the darkness."},
]

# --------------------------------------------------------------- framing
#
# `supports` lists which of the above a framing may be combined with, so a
# combination you do not offer simply cannot be chosen.
#
FRAMINGS = [
    {"id": "none", "label": "Unframed",
     "note": "Shipped flat, ready for your own framer.",
     "supports": ["paper", "plexi"]},
    {"id": "caisse", "label": "Caisse américaine",
     "note": "Solid wood floater frame, the print set back from the edge.",
     "supports": ["paper", "plexi"]},
]

# What is printed under the price. Say the true thing; leave it empty to
# show nothing.
EDITION = "Printed to order in Paris. Signed on the reverse."

# Roughly how long between the order and the parcel. Shown in the panel and
# repeated on the confirmation page.
LEAD_TIME = "Allow two to three weeks."

# Shipping is collected by Stripe at checkout, so the price above is the
# print alone. Each entry is a country list and a price; the first entry is
# the default shown in the panel.
SHIPPING = [
    {"id": "fr", "label": "France", "price": 15, "countries": ["FR"]},
    {"id": "eu", "label": "Europe", "price": 25,
     "countries": ["BE", "DE", "ES", "IT", "LU", "NL", "PT", "AT", "IE", "DK", "SE", "FI", "PL", "CZ"]},
    {"id": "uk", "label": "United Kingdom", "price": 25, "countries": ["GB"]},
    {"id": "world", "label": "Rest of the world", "price": 45,
     "countries": ["US", "CA", "CH", "NO", "AU", "NZ", "JP"]},
]


# ------------------------------------------------------------------ logic
# Below here is machinery, not settings. You should not need to edit it.

def format_by_id(fid):
    for f in FORMATS:
        if f["id"] == fid:
            return f
    return None


def support_by_id(sid):
    for s in SUPPORTS:
        if s["id"] == sid:
            return s
    return None


def framing_by_id(gid):
    for g in FRAMINGS:
        if g["id"] == gid:
            return g
    return None


def price(fid, sid, gid):
    """What one print costs, in euros, or None if that is not something
    you sell. Every price the site shows and every price Stripe charges
    comes through here."""
    fmt, sup, frm = format_by_id(fid), support_by_id(sid), framing_by_id(gid)
    if not fmt or not sup or not frm:
        return None
    if sup["id"] not in frm["supports"]:
        return None
    total = fmt.get(sup["id"])
    if total is None:
        return None
    if frm["id"] != "none":
        total += fmt.get("frame", 0)
    return total


def cents(euros):
    """Stripe charges in the currency's smallest unit."""
    return int(round(float(euros) * 100))


def describe(fid, sid, gid):
    """The one line that names this print on the invoice and in the
    dashboard, so an order can be filled without opening anything else."""
    fmt, sup, frm = format_by_id(fid), support_by_id(sid), framing_by_id(gid)
    if not fmt or not sup or not frm:
        return None
    line = "%d cm long edge, %s" % (fmt["edge"], sup["label"].lower())
    if frm["id"] != "none":
        line += ", %s" % frm["label"].lower()
    return line


def priced():
    """True once at least one real price has been entered. The order button
    stays hidden until then, so a half-filled price list can never take a
    payment for nothing."""
    return any(f.get("paper") or f.get("plexi") for f in FORMATS)


def config():
    """The shop as the browser needs it: options, prices and copy, ready to
    be dropped into a page as JSON. Prices are in euros here — the panel
    only displays them, and the server prices the order again from this same
    file before charging anything."""
    return {
        "currency": CURRENCY,
        "symbol": SYMBOL,
        "endpoint": CHECKOUT_ENDPOINT,
        "email": ENQUIRY_EMAIL,
        "edition": EDITION,
        "leadTime": LEAD_TIME,
        "formats": [
            {"id": f["id"], "edge": f["edge"],
             "prices": {
                 s["id"]: {
                     g["id"]: price(f["id"], s["id"], g["id"])
                     for g in FRAMINGS
                 } for s in SUPPORTS
             }}
            for f in FORMATS
        ],
        "supports": [{"id": s["id"], "label": s["label"], "note": s["note"]}
                     for s in SUPPORTS],
        "framings": [{"id": g["id"], "label": g["label"], "note": g["note"],
                      "supports": g["supports"]} for g in FRAMINGS],
        "shipping": [{"id": s["id"], "label": s["label"], "price": s["price"]}
                     for s in SHIPPING],
    }
