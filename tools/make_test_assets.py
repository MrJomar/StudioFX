"""Genera imagenes y clips sinteticos de prueba (para no depender de material con derechos)."""
import os
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets_prueba")
os.makedirs(OUT, exist_ok=True)
PALETTES = [
    ((20, 30, 60), (230, 150, 80)), ((40, 20, 40), (240, 120, 100)), ((15, 40, 50), (200, 220, 140)),
    ((50, 35, 20), (250, 200, 110)), ((20, 20, 35), (120, 160, 230)), ((45, 25, 25), (230, 90, 70)),
    ((10, 35, 30), (150, 220, 200)), ((35, 30, 50), (220, 180, 240)), ((55, 40, 15), (255, 220, 120)),
    ((25, 25, 25), (200, 200, 190)), ((30, 20, 55), (255, 140, 170)),
]


def make_image(i, W=2400, H=1600):
    rng = np.random.default_rng(100 + i)
    top, sun = PALETTES[i % len(PALETTES)]
    y = np.linspace(0, 1, H)[:, None, None]
    sky = np.array(top)[None, None, :] * (1 - y) + np.array(sun)[None, None, :] * y * 0.9
    img = np.repeat(sky, W, axis=1).astype(np.float32)
    xx, yy = np.meshgrid(np.arange(W), np.arange(H))
    sx, sy = rng.uniform(0.2, 0.8) * W, rng.uniform(0.25, 0.5) * H
    glow = np.exp(-(((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * (W * 0.12) ** 2)))[..., None]
    img += glow * np.array(sun)[None, None, :] * 0.6
    for layer in range(4):  # siluetas de "edificios/montanas"
        base = H * (0.55 + layer * 0.1)
        xs = np.arange(W)
        prof = base - 90 * (np.sin(xs / rng.uniform(60, 160) + layer) + 0.6 * np.sin(xs / rng.uniform(25, 60)))
        prof -= (rng.random(W // 40 + 1).repeat(40)[:W] > 0.6) * rng.uniform(40, 120)
        mask = yy > prof[None, :]
        shade = 0.12 + layer * 0.08
        img[mask] = img[mask] * 0.25 + np.array(top) * shade
    img += rng.normal(0, 3, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    pil = Image.fromarray(img)
    d = ImageDraw.Draw(pil)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    d.text((int(W*0.5) - 300, int(H*0.50)), "IMAGEN DE PRUEBA %02d" % (i + 1), font=f, fill=(255, 255, 255))
    for k in range(6):  # marcas de referencia para ver el movimiento
        cx = int(W * (k + 0.5) / 6)
        d.ellipse([cx - 14, 300 - 14, cx + 14, 300 + 14], outline=(255, 255, 255), width=4)
        d.line([cx, 250, cx, 330], fill=(255, 255, 255), width=3)
    pil.save(os.path.join(OUT, "img%02d.jpg" % (i + 1)), quality=92)


for i in range(11):
    make_image(i)

for i, (c0, c1) in enumerate([("0x1b2a49", "0xe8a05a"), ("0x2b1b2e", "0xf0806a"), ("0x10303a", "0xc8dc8c")]):
    out = os.path.join(OUT, "clip%02d.mp4" % (i + 1))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "gradients=s=1280x720:d=4:r=30:c0=%s:c1=%s:speed=0.05:type=%d" % (c0, c1, i % 3),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out], check=True)
print("assets ok:", sorted(os.listdir(OUT)))
