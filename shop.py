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
# It is True so the prices show on the published site. Be clear about what
# that means today: CHECKOUT_ENDPOINT is answered by checkout_server.py,
# GitHub Pages serves files and nothing else, so the panel opens and prices
# correctly but "Continue to payment" cannot reach anything. The panel
# catches that and offers ENQUIRY_EMAIL instead, which is a soft landing
# rather than a working till. Host checkout_server.py to close the gap.
OPEN = True


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
# The numbers are WhiteWall's list price for the same piece, multiplied by
# 2.5 and rounded to the nearest five euros. Read from whitewall.com/fr on
# 18 September 2026, prices TTC, carriage excluded.
#
# A format here is a longest edge, but WhiteWall sells rectangles, so each
# row is priced against the smallest standard 3:2 size whose long side
# reaches this edge — 45x30, 60x40, 90x60, 105x70. The catalogue entries
# behind each column:
#
#   paper  Impression Fine Art, Hahnemuehle Photo Rag
#          24,95 / 33,95 / 68,95 / 91,95
#   plexi  Tirage photo sous Plexi — Fuji Crystal Archive brillant sous
#          verre acrylique 2 mm, 103,95 / 141,95 / 271,95 / 352,95
#   frame  le meme tirage en cadre Bale 15 mm a joint d'ombre,
#          185,95 / 225,95 / 370,95 / 463,95, moins le prix plexi
#          ci-dessus — soit 82 / 84 / 99 / 111 pour l'encadrement seul.
#          Ce supplement est le meme sur l'impression pigmentaire Fine
#          Art sous plexi, qui coute bien plus cher au tirage : le cadre
#          se facture a part et ne depend pas du tirage qu'il entoure.
#
# Two things the 3:2 reference does not cover, both worth knowing before
# you quote a plate that is not a 3:2:
#
#   A square print is the same long edge but half again the area, and
#   WhiteWall charges for area. A 100x100 under plexi in its frame is
#   538,95 against the 463,95 of the 105x70 this row is priced on. The
#   2.5 absorbs it — you would still be near 2.1 — but it is not free.
#
#   WhiteWall does not mount fine art paper in a shadow-gap frame at all.
#   Paper is offered with conventional wood mouldings and a passe-partout,
#   which costs far more than the plexi framing above: 156 at 60x40, 201
#   at 90x60, and nothing beyond 90x60. So the frame column below is
#   honest for plexi and too cheap for paper, and FRAMINGS still offers
#   the caisse on both. Either drop "paper" from its supports list or
#   find the framing somewhere other than WhiteWall.
FORMATS = [
    {"id": "40",  "edge": 40,  "paper": 60,  "plexi": 260, "frame": 205},
    {"id": "60",  "edge": 60,  "paper": 85,  "plexi": 355, "frame": 210},
    {"id": "80",  "edge": 80,  "paper": 170, "plexi": 680, "frame": 250},
    {"id": "100", "edge": 100, "paper": 230, "plexi": 880, "frame": 280},
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

# Carriage, and the one combination that pays for it.
#
# Everything the shop sells carries its transport in the price already —
# except the bare paper print, which is the only thing cheap enough that a
# parcel would eat the margin. A 40 cm paper print sells for 60 against
# 24,95 of printing; absorbing 15 of carriage would leave 20, a third of
# what every other row holds. So that one combination adds the carriage at
# checkout and the rest do not.
#
# The band also decides where a parcel may go: checkout_server.py builds
# its allowed countries from this list, so France alone is what Stripe
# will accept an address in. To open another country, add its band here.
SHIPPING = [
    {"id": "fr", "label": "France", "price": 15, "countries": ["FR"]},
]

# The combinations that pay the carriage above rather than having it in the
# price already, as (support, framing) pairs. Anything not listed here is
# delivered included.
CARRIAGE_PAID_BY = [("paper", "none")]


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


def carriage(sid, gid, band=None):
    """What this combination adds for transport, in euros, on top of what
    price() returns. Zero for everything but the bare paper print.

    The panel shows this and checkout_server.py charges it, both from
    here, so the line the buyer reads and the line Stripe bills can never
    drift apart."""
    if (sid, gid) not in CARRIAGE_PAID_BY:
        return 0
    band = band or (SHIPPING[0] if SHIPPING else None)
    return band["price"] if band else 0


def carriage_included(sid, gid):
    """True when the price already covers the parcel. What the panel says
    under the total is written from this."""
    return (sid, gid) not in CARRIAGE_PAID_BY


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
        # What each combination adds for transport, so the panel can say
        # "shipping included" or name the sum without knowing the rule.
        "carriage": {
            s["id"]: {g["id"]: carriage(s["id"], g["id"]) for g in FRAMINGS}
            for s in SUPPORTS
        },
    }
