"""Gera preview de rosto real (para o app.png) e personas circulares com landmarks.

Saídas: /tmp/preview_face.png e docs/assets/persona{1,2,3}.png
"""
import glob
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont

mp_face = mp.solutions.face_mesh
mp_draw = mp.solutions.drawing_utils
green = mp_draw.DrawingSpec(color=(120, 230, 100), thickness=1, circle_radius=0)


def font(sz, bold=False):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", sz)
    except Exception:
        return ImageFont.load_default()


def process(path, mesh=True):
    bgr = cv2.imread(path)
    if bgr is None:
        return None
    h, w = bgr.shape[:2]
    with mp_face.FaceMesh(static_image_mode=True, refine_landmarks=True, max_num_faces=1) as fm:
        res = fm.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    lm = res.multi_face_landmarks[0]
    if mesh:
        mp_draw.draw_landmarks(bgr, lm, mp_face.FACEMESH_TESSELATION, None, green)
    xs = [p.x * w for p in lm.landmark]; ys = [p.y * h for p in lm.landmark]
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return img, (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))


def make_preview(path, out, size=(560, 420)):
    """Rosto real recortado para a área de preview do app, com bbox."""
    img, (x0, y0, x1, y1) = process(path)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    half_w = int((x1 - x0) * 0.95); half_h = int((y1 - y0) * 0.75)
    L = max(cx - int(size[0] / size[1] * half_h), 0); R = min(cx + int(size[0] / size[1] * half_h), img.size[0])
    T = max(cy - half_h - 30, 0); B = min(cy + half_h + 40, img.size[1])
    face = img.crop((L, T, R, B)).resize(size)
    canvas = Image.new("RGB", size, (0, 0, 0))
    canvas.paste(face, (0, 0))
    d = ImageDraw.Draw(canvas)
    bx0 = int((x0 - L) / (R - L) * size[0]); by0 = int((y0 - T) / (B - T) * size[1])
    bx1 = int((x1 - L) / (R - L) * size[0]); by1 = int((y1 - T) / (B - T) * size[1])
    d.rectangle([bx0, by0, bx1, by1], outline=(76, 141, 255), width=2)
    d.text((12, size[1] - 26), "captura ao vivo · 478 landmarks", font=font(13, True), fill=(180, 200, 255))
    canvas.save(out)
    print("OK", out)


def make_persona(path, out, ring, label, size=240):
    img, (x0, y0, x1, y1) = process(path)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    half = int(max(x1 - x0, y1 - y0) * 0.8)
    crop = img.crop((max(cx - half, 0), max(cy - half, 0),
                     min(cx + half, img.size[0]), min(cy + half, img.size[1]))).resize((size, size))
    # máscara circular
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([6, 6, size - 6, size - 6], fill=255)
    out_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out_img.paste(crop, (0, 0), mask)
    d = ImageDraw.Draw(out_img)
    d.ellipse([4, 4, size - 4, size - 4], outline=ring, width=5)
    out_img.save(out)
    print("OK", out, "-", label)


faces = sorted(glob.glob("/tmp/real_face_*.jpg"))
make_preview(faces[5], "/tmp/preview_face.png")
make_persona(faces[6], "docs/assets/persona1.png", (76, 141, 255), "Profissional de saúde")
make_persona(faces[7], "docs/assets/persona2.png", (255, 176, 32), "Pesquisador(a)")
make_persona(faces[8], "docs/assets/persona3.png", (62, 207, 142), "Pessoa em triagem")
