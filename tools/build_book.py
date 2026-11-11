"""Build book/index.html (self-contained, works from file://).
Scenes with a layers.json are rendered as animated paper-cut rigs, the others as
a static illustration with a gentle camera move until their layers are made.
"""
import json, os, shutil
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, "book")
PAGES_OUT = os.path.join(BOOK, "assets", "pages")
os.makedirs(PAGES_OUT, exist_ok=True)

ANIMATE_P01 = False  # book is static-only for now
CAPTIONS = [
    "Ciao Matilde",
    "O come ti chiamo io “Matidde”",
    "O come ti chiamerà Attilio “Mamma”",
    "In un anno sono cambiate un sacco di cose.",
    "Tu hai perso un po’ di pancia",
    "Io ho acquistato un po’ di pancia.",
    "Abbiamo buttato via delle cose",
    "Ne abbiamo comprato delle altre",
    "Ma soprattutto da due siamo diventati tre.",
    "Ci sono un sacco di duo famosi",
    "Ma le vere band sono sempre formate da un power trio.",
    "A volte il cambiamento fa paura",
    "A volte non so più chi sono, e cosa sto facendo",
    "Ma quello che so è che ogni anno ti amo sempre di più.",
    "Per la bellissima donna che sei",
    "Per la compagna migliore che c’è",
    "Per la mamma migliore che c’è",
    "Buon anniversario amore mio e grazie per essere sempre qui.",
    "Con noi.",
]

# static jpgs for every page
for i in range(1, len(CAPTIONS) + 1):
    src = os.path.join(ROOT, "pages", f"p{i:02d}.png")
    dst = os.path.join(PAGES_OUT, f"p{i:02d}.jpg")
    if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
        Image.open(src).convert("RGB").save(dst, quality=88)

# ---------- page 1 rig ----------
def skin_around(orig, cx, cy, r):
    h, w = orig.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    d = np.hypot(xs - cx, ys - cy)
    ring = (d > r * 1.3) & (d < r * 2.4)
    px = orig[ring].astype(int)
    ok = (px[:, 0] > 200) & (px[:, 0] - px[:, 1] > 40) & (px[:, 1] > 110) & (px[:, 2] < 150)
    px = px[ok]
    c = np.median(px, axis=0).astype(int) if len(px) else (244, 160, 100)
    return "#%02x%02x%02x" % tuple(c)

def rig_p01():
    A = os.path.join(BOOK, "assets", "p01")
    data = json.load(open(os.path.join(A, "layers.json")))
    W, H = data["size"]
    L = data["layers"]
    orig = np.array(Image.open(os.path.join(ROOT, "pages", "p01.png")).convert("RGB"))

    def box(name, cls, extra="", inner=""):
        l = L[name]
        px, py = l["pivot"] if l["pivot"] else (l["x"] + l["w"] / 2, l["y"] + l["h"] / 2)
        ox = (px - l["x"]) / l["w"] * 100
        oy = (py - l["y"]) / l["h"] * 100
        return (f'<div class="L {cls}" style="left:{l["x"]/W*100:.3f}%;top:{l["y"]/H*100:.3f}%;'
                f'width:{l["w"]/W*100:.3f}%;height:{l["h"]/H*100:.3f}%;transform-origin:{ox:.1f}% {oy:.1f}%">'
                f'<img src="assets/p01/{name}.png" alt="" draggable="false">{inner}</div>')

    def lids(layer, eyes):
        l = L[layer]
        out = [f'<svg class="lids" viewBox="{l["x"]} {l["y"]} {l["w"]} {l["h"]}" preserveAspectRatio="none">']
        for k, (cx, cy, rx, ry) in enumerate(eyes):
            col = skin_around(orig, cx, cy, max(rx, ry))
            out.append(
                f'<g class="lid lid{k}"><ellipse cx="{cx}" cy="{cy}" rx="{rx+3}" ry="{ry+3}" fill="{col}"/>'
                f'<path d="M{cx-rx-2} {cy+ry*0.35} Q{cx} {cy+ry*1.25} {cx+rx+2} {cy+ry*0.35}" '
                f'fill="none" stroke="#2b2626" stroke-width="3.2" stroke-linecap="round"/></g>')
        out.append("</svg>")
        return "".join(out)

    html = f'''<div class="rig p01" style="aspect-ratio:{W}/{H}">
  <img class="L plate" src="assets/p01/plate.jpg" alt="" draggable="false">
  {box("shadows","shadows")}
  <div class="actor papa"><div class="breath">
    {box("flowers","flowers")}
    {box("papa_arm","arm")}
    {box("papa_body","body")}
    {box("papa_head","head",inner=lids("papa_head",[(249,213,15,8),(298,197,10,11)]))}
  </div></div>
  <div class="actor mamma"><div class="breath">
    {box("mamma_body","body")}
    {box("mamma_head","head",inner=lids("mamma_head",[(667,236,9,12),(708,246,11,10)]))}
  </div></div>
  {box("sparkles","sparkles")}
</div>'''
    return html

pages_html = []
for i, cap in enumerate(CAPTIONS, 1):
    rigged = os.path.exists(os.path.join(BOOK, "assets", f"p{i:02d}", "layers.json"))
    if i == 1 and rigged and ANIMATE_P01:
        scene = rig_p01()
    else:
        scene = (f'<div class="rig still" style="aspect-ratio:896/1120">'
                 f'<img class="L plate kb" src="assets/pages/p{i:02d}.jpg" alt="" draggable="false"></div>')
    pages_html.append(
        f'<section class="page" data-i="{i}"><div class="frame">{scene}'
        f'<p class="cap">{cap}</p></div></section>')

tpl = open(os.path.join(ROOT, "tools", "book_template.html"), encoding="utf-8").read()
out = tpl.replace("<!--PAGES-->", "\n".join(pages_html)).replace("__N__", str(len(CAPTIONS)))
open(os.path.join(BOOK, "index.html"), "w", encoding="utf-8").write(out)
print("built", len(CAPTIONS), "pages; rigged p01:", os.path.exists(os.path.join(BOOK, "assets", "p01", "layers.json")))

# self-contained copy: every image inlined, works anywhere (also in previews that block relative files)
import base64, re
html = open(os.path.join(BOOK, "index.html"), encoding="utf-8").read()
def inline(m):
    p = os.path.join(BOOK, m.group(1))
    mime = "image/png" if p.endswith(".png") else "image/jpeg"
    return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(open(p, "rb").read()).decode())
html = re.sub(r'src="(assets/[^"]+)"', inline, html)
open(os.path.join(ROOT, "libro.html"), "w", encoding="utf-8").write(html)
print("libro.html", round(len(html) / 1e6, 1), "MB")
