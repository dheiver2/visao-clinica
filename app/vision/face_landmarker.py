"""Face Landmarker de alta precisão (MediaPipe Tasks).

Usa o modelo oficial `face_landmarker.task`, que entrega:
- 478 landmarks faciais 3D (com íris refinada),
- 52 **blendshapes** (intensidades de Action Units, estilo FACS) — medidas reais,
  não proxies geométricos,
- matriz de transformação facial (pose da cabeça).

Os blendshapes elevam a precisão dos biomarcadores faciais (hipomimia, micro-
expressões, assimetria, piscar, olhar). O modelo é baixado uma vez e cacheado
localmente (depois funciona offline) — encapsulado, sem configuração manual.

Referência do modelo: MediaPipe Face Landmarker (Google), baseado na arquitetura
de malha facial de Kartynnik et al., "Real-time Facial Surface Geometry from
Monocular Video on Mobile GPUs" (2019).
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from app.paths import bundled_models_dir, models_dir

# Asset embutido no bundle (read-only); se ausente, baixa para a área gravável.
_BUNDLED = bundled_models_dir() / "face_landmarker.task"
MODEL_PATH = _BUNDLED if _BUNDLED.exists() else models_dir() / "face_landmarker.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")

try:
    import mediapipe as mp
    from mediapipe.tasks import python as _mp_python
    from mediapipe.tasks.python import vision as _mp_vision
    _TASKS_OK = True
except Exception:  # pragma: no cover
    _TASKS_OK = False


@dataclass
class FaceResult:
    landmarks: list           # NormalizedLandmark (x, y, z) — 478 pontos
    blendshapes: dict = field(default_factory=dict)  # nome -> score 0..1
    head_pose: object = None  # matriz 4x4 de transformação facial (ou None)


def ensure_model(progress=None) -> Path | None:
    """Garante o modelo .task localmente; baixa na 1ª vez."""
    if MODEL_PATH.exists():
        return MODEL_PATH
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        if progress:
            progress("Baixando modelo Face Landmarker (alta precisão)…")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return MODEL_PATH
    except Exception:  # noqa: BLE001
        return None


class FaceLandmarker:
    """Wrapper do Face Landmarker com blendshapes e pose da cabeça."""

    def __init__(self, progress=None):
        self._lm = None
        if not _TASKS_OK:
            return
        path = ensure_model(progress)
        if not path:
            return
        base = _mp_python.BaseOptions(model_asset_path=str(path))
        opts = _mp_vision.FaceLandmarkerOptions(
            base_options=base,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
            running_mode=_mp_vision.RunningMode.IMAGE,
        )
        self._lm = _mp_vision.FaceLandmarker.create_from_options(opts)

    def available(self) -> bool:
        return self._lm is not None

    def detect(self, rgb) -> FaceResult | None:
        """Processa um frame RGB (numpy HxWx3, uint8) e retorna FaceResult."""
        if self._lm is None:
            return None
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self._lm.detect(image)
        if not res.face_landmarks:
            return None
        bs = {}
        if res.face_blendshapes:
            bs = {c.category_name: float(c.score) for c in res.face_blendshapes[0]}
        pose = None
        if getattr(res, "facial_transformation_matrixes", None):
            pose = res.facial_transformation_matrixes[0]
        return FaceResult(landmarks=res.face_landmarks[0], blendshapes=bs, head_pose=pose)
