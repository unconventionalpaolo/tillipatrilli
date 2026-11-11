"""Split page 1 into animatable paper-cut layers (v2: clean edges, underlaps, no ghosts).
Inputs : work/p01/cut.png (characters, alpha), work/p01/plate_raw.png (empty bg), pages/p01.png (original)
Output : book/assets/p01/*.png + layers.json (x,y,w,h in 896x1120 space)
Z-order (back->front): plate, shadows, flowers, papa_arm, papa_body, papa_head, mamma_body, mamma_head, sparkles
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, "work", "p01")
OUT = os.path.join(ROOT, "book", "assets", "p01")
os.makedirs(OUT, exist_ok=True)

cut = np.array(Image.open(os.path.join(W, "cut.png")).convert("RGBA"))
plate = Image.open(os.path.join(W, "plate_raw.png")).convert("RGB")
orig = np.array(Image.open(os.path.join(ROOT, "pages", "p01.png")).convert("RGB"))
H, Wd = cut.shape[:2]
SIZE = (Wd, H)
yy, xx = np.mgrid[0:H, 0:Wd]

def poly(points):
    m = Image.new("L", SIZE, 0)
    ImageDraw.Draw(m).polygon(points, fill=255)
    return np.array(m) > 0

def rect(x0, y0, x1, y1):
    m = np.zeros((H, Wd), bool); m[y0:y1, x0:x1] = True; return m

def clean_components(mask, min_px):
    lab, n = ndi.label(mask)
    if n == 0: return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sizes >= min_px
    return keep[lab]

def defringe(rgb, mask, depth=3):
    """replace colours of the outer `depth` px by the nearest deep-interior colour (kills the cream halo)"""
    inner = ndi.binary_erosion(mask, iterations=depth)
    if inner.sum() == 0: return rgb
    idx = ndi.distance_transform_edt(~inner, return_distances=False, return_indices=True)
    out = rgb[idx[0], idx[1]]
    ring = mask & ~inner
    res = rgb.copy(); res[ring] = out[ring]
    return res

def soft(mask):
    return np.clip(ndi.gaussian_filter(mask.astype(float), 0.7) * 1.15, 0, 1)

layers = {}
def save(name, rgb, alpha_f, pivot=None):
    a = np.zeros((H, Wd, 4), np.uint8); a[..., :3] = rgb; a[..., 3] = (alpha_f * 255).astype(np.uint8)
    img = Image.fromarray(a, "RGBA"); bbox = img.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    if bbox is None: print("EMPTY", name); return
    crop = img.crop(bbox); crop.save(os.path.join(OUT, name + ".png"), optimize=True)
    layers[name] = {"x": bbox[0], "y": bbox[1], "w": crop.size[0], "h": crop.size[1], "pivot": pivot}

plate.save(os.path.join(OUT, "plate.jpg"), quality=90)
layers["plate"] = {"x": 0, "y": 0, "w": Wd, "h": H, "pivot": None}

# ---------- clean the cutout: binary alpha, no specks, eroded 1px, defringed colour
a0 = cut[..., 3] >= 128
a0 = clean_components(a0, 600)
a0 = ndi.binary_fill_holes(a0)
a0 = ndi.binary_erosion(a0, iterations=1)
rgb = defringe(cut[..., :3], a0, 3)
orig_rgb = orig

# ---------- residues taken from the original (flowers / shadows / sparkles)
pl = np.array(plate)
diff = np.abs(orig.astype(int) - pl.astype(int)).sum(2)
near_char = ndi.binary_dilation(a0, iterations=2)

def blob(box, thr, min_px, open_it=0, close_it=3, exclude_char=True):
    m = (diff > thr) & rect(*box)
    if exclude_char: m &= ~near_char
    if open_it: m = ndi.binary_opening(m, iterations=open_it)
    m = ndi.binary_closing(m, iterations=close_it, structure=np.ones((3, 3)))
    m = ndi.binary_fill_holes(m)
    m = clean_components(m, min_px)
    return ndi.binary_dilation(m, iterations=1)

shadows = blob((30, 770, 860, 840), 45, 800)
sparkles = blob((560, 95, 660, 185), 60, 150, close_it=2)
fl = blob((20, 300, 175, 550), 28, 500, open_it=2, close_it=4)
fl_rgb = defringe(orig_rgb, fl, 2)
save("shadows", orig_rgb, soft(shadows))
save("sparkles", defringe(orig_rgb, sparkles, 2), soft(sparkles), pivot=(615, 180))
save("flowers", fl_rgb, soft(fl), pivot=(120, 500))

# ---------- PAPA (x < 505)
alpha_p = a0 & rect(0, 0, 505, H)
# head = everything above the beard line (neck + shirt stay with the body)
head_poly = poly([(150, 90), (372, 90), (372, 262), (358, 282), (346, 296), (330, 301), (312, 304), (300, 307),
                  (285, 314), (260, 312), (232, 304), (208, 292), (190, 278), (150, 272)])
head_p = alpha_p & head_poly

# arm = hand + forearm, cut against the sleeve cuff by colour
skin = (rgb[..., 0] > 165) & (rgb[..., 0] - rgb[..., 2] > 55) & (rgb[..., 0] > rgb[..., 1] + 22)
skin = ndi.binary_closing(ndi.binary_opening(skin, iterations=1), iterations=2)
band = rect(362, 296, 412, 396)
arm_zone = rect(362, 150, 520, 396) & ~head_poly
arm_m = alpha_p & arm_zone & (~band | skin)
arm_m = clean_components(arm_m, 800)
arm_m = ndi.binary_fill_holes(arm_m)

body_m = alpha_p & ~head_p & ~arm_m
body_m = clean_components(body_m, 800)
body_rgb = rgb.copy()

# under-head fill: dark beard/shadow strip so the neck never shows a hole when the head tilts
under = poly([(236, 284), (350, 284), (346, 300), (330, 312), (300, 322), (262, 320), (244, 308)]) & ~body_m
under &= ndi.binary_dilation(alpha_p, iterations=4)
body_rgb[under] = (44, 36, 32)
body_m = body_m | under

# arm underlap: skin-coloured continuation hidden under the sleeve (arm layer is BEHIND the body)
skin_col = np.median(rgb[arm_m & skin & (yy > 300) & (yy < 360)], axis=0).astype(np.uint8)
body_in = ndi.binary_erosion(body_m, iterations=7)
fill = body_in & rect(352, 332, 416, 376) & ~arm_m
arm_rgb = rgb.copy(); arm_rgb[fill] = skin_col
arm_full = arm_m | fill

save("papa_arm", arm_rgb, soft(arm_full), pivot=(392, 350))
save("papa_body", body_rgb, soft(body_m), pivot=(300, 700))
save("papa_head", rgb, soft(head_p), pivot=(290, 320))

# ---------- MAMMA
alpha_m = a0 & rect(500, 100, 880, 840)
head_poly_m = poly([(540, 90), (870, 90), (870, 288), (738, 288), (726, 300), (692, 308),
                    (655, 306), (640, 296), (632, 288), (540, 288)])
head_poly_m = head_poly_m | rect(726, 288, 752, 318)
head_mm = alpha_m & head_poly_m
body_mm = alpha_m & ~head_poly_m
body_mm = clean_components(body_mm, 800)
# overlap band: copy of the hair just above the seam, plus a skin/dark fill for the neck
band_m = alpha_m & rect(540, 262, 870, 290)
body_mm_all = body_mm | band_m
body_mm_rgb = rgb.copy()
neck = poly([(635, 270), (735, 270), (735, 312), (635, 312)]) & ~body_mm_all
body_mm_rgb[neck] = (205, 120, 70)
body_mm_all |= neck & ndi.binary_dilation(alpha_m, iterations=2)
save("mamma_body", body_mm_rgb, soft(body_mm_all), pivot=(670, 700))
save("mamma_head", rgb, soft(head_mm), pivot=(690, 300))

json.dump({"size": [Wd, H], "layers": layers}, open(os.path.join(OUT, "layers.json"), "w"), indent=1)
print({k: (v["x"], v["y"], v["w"], v["h"]) for k, v in layers.items()})
