"""Processa rostos fotorrealistas (IA, pessoas inexistentes) com MediaPipe real
e gera o hero + galeria com a malha de landmarks autêntica.

Entradas: /tmp/real_face_{1..5}.jpg
Saídas: docs/assets/face_mesh.png (hero) e real_var{1,2,3}.png (galeria)
"""
import glob
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont

mp_face = mp.solutions.face_mesh
mp_draw = mp.solutions.drawing_utils
TESS = mp_face.FACEMESH_TESSELATION
CONT = mp_face.FACEMESH_CONTOURS

GREEN = (128, 255, 62)   # BGR-ish (cv2 usa BGR) -> usamos (B,G,R)
green_spec = mp_draw.DrawingSpec(color=(120, 230, 100), thickness=1, circle_radius=0)
dot_spec = mp_draw.DrawingSpec(color=(120, 230, 100), thickness=1, circle_radius=1)


def font(sz, bold=False):
    path = "/System/Library/Fonts/Helvetica.ttc"
    try:
        return ImageFont.truetype(path, sz)
    except Exception:
        return ImageFont.load_default()


def process(path):
    """Retorna (PIL RGB com malha, bbox px) ou None se não detectar rosto."""
    bgr = cv2.imread(path)
    if bgr is None:
        return None
    h, w = bgr.shape[:2]
    with mp_face.FaceMesh(static_image_mode=True, refine_landmarks=True,
                          max_num_faces=1) as fm:
        res = fm.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    lm = res.multi_face_landmarks[0]
    mp_draw.draw_landmarks(bgr, lm, TESS, None, green_spec)
    mp_draw.draw_landmarks(bgr, lm, CONT, None,
                           mp_draw.DrawingSpec(color=(255, 200, 80), thickness=1))
    xs = [p.x * w for p in lm.landmark]; ys = [p.y * h for p in lm.landmark]
    bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb), bbox


def rounded(img, rad):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0], img.size[1]], rad, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def make_tile(path, out, size=(320, 360)):
    r = process(path)
    if not r:
        return False
    img, (x0, y0, x1, y1) = r
    # recorte quadrado centrado no rosto, com folga
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    half = int(max(x1 - x0, y1 - y0) * 0.85)
    L = max(cx - half, 0); T = max(cy - half, 0)
    R = min(cx + half, img.size[0]); B = min(cy + half, img.size[1])
    crop = img.crop((L, T, R, B)).resize((size[0] - 16, size[0] - 16))
    card = Image.new("RGB", size, (20, 22, 27))
    card.paste(crop, (8, 8))
    d = ImageDraw.Draw(card)
    # bbox azul relativo ao recorte
    bx0 = int((x0 - L) / (R - L) * (size[0] - 16)) + 8
    by0 = int((y0 - T) / (B - T) * (size[0] - 16)) + 8
    bx1 = int((x1 - L) / (R - L) * (size[0] - 16)) + 8
    by1 = int((y1 - T) / (B - T) * (size[0] - 16)) + 8
    d.rectangle([bx0, by0, bx1, by1], outline=(76, 141, 255), width=2)
    d.text((12, size[1] - 26), "rosto detectado", font=font(13), fill=(140, 144, 155))
    rounded(card, 14).save(out)
    print("OK", out)
    return True


def make_hero(path, out):
    r = process(path)
    if not r:
        return False
    img, (x0, y0, x1, y1) = r
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    half = int(max(x1 - x0, y1 - y0) * 0.95)
    L = max(cx - half, 0); T = max(cy - int(half * 1.1), 0)
    R = min(cx + half, img.size[0]); B = min(cy + int(half * 1.15), img.size[1])
    face = img.crop((L, T, R, B))
    fw = 470; fh = int(face.size[1] * fw / face.size[0])
    face = face.resize((fw, fh))

    W, H = 960, max(560, fh + 90)
    canvas = Image.new("RGB", (W, H), (8, 10, 14))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([8, 8, W - 8, H - 8], 14, outline=(42, 46, 55), width=2)
    fx, fy = 40, (H - fh) // 2
    canvas.paste(face, (fx, fy))
    # bbox + cantos
    bx0 = fx + int((x0 - L) / (R - L) * fw); by0 = fy + int((y0 - T) / (B - T) * fh)
    bx1 = fx + int((x1 - L) / (R - L) * fw); by1 = fy + int((y1 - T) / (B - T) * fh)
    d.rectangle([bx0, by0, bx1, by1], outline=(76, 141, 255), width=2)
    d.text((bx0, by0 - 22), "ROSTO DETECTADO · 478 landmarks", font=font(13, True), fill=(76, 141, 255))
    # painel lateral
    px = 660
    d.rounded_rectangle([px, 70, px + 250, H - 70], 12, fill=(20, 22, 27))
    d.text((px + 16, 84), "INDICADORES CLÍNICOS", font=font(11, True), fill=(139, 144, 155))
    rows = [("Tremor parkinsoniano", (255, 92, 92), 0.85),
            ("Sinais de TEA (autismo)", (255, 92, 92), 0.80),
            ("Tipo Alzheimer", (255, 176, 32), 0.6),
            ("Assimetria facial", (255, 176, 32), 0.55),
            ("Estresse / ansiedade", (62, 207, 142), 0.25),
            ("Sonolência", (62, 207, 142), 0.15)]
    y = 112
    for name, col, val in rows:
        d.rounded_rectangle([px + 14, y, px + 236, y + 46], 8, fill=(27, 30, 37))
        d.text((px + 24, y + 8), name, font=font(12), fill=(230, 232, 236))
        d.rounded_rectangle([px + 24, y + 28, px + 224, y + 34], 3, fill=(10, 11, 14))
        d.rounded_rectangle([px + 24, y + 28, px + 24 + int(200 * val), y + 34], 3, fill=col)
        y += 56
    d.text((px + 16, y + 6), "FC 76 bpm · VFC 38 ms", font=font(14, True), fill=(255, 92, 92))
    canvas.save(out)
    print("OK", out)
    return True


faces = sorted(glob.glob("/tmp/real_face_*.jpg"))
done = []
for f in faces:
    r = process(f)
    if r:
        done.append(f)
print("rostos com face detectada:", len(done))
make_hero(done[0], "docs/assets/face_mesh.png")
for i, f in enumerate(done[1:4], 1):
    make_tile(f, f"docs/assets/real_var{i}.png")
