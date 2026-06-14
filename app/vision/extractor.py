"""Extração de biomarcadores a partir da webcam usando OpenCV + MediaPipe.

Pipeline: Webcam -> Face Mesh + Pose + Hands -> features agregadas.

A extração detalhada de cada marcador é organizada em métodos privados para
manter o pipeline legível. Onde o cálculo fino ainda não foi implementado,
o método retorna 0.0 e registra a série temporal correspondente para
processamento posterior (Dask).
"""

from __future__ import annotations

import time
from collections import defaultdict

import numpy as np

from .features import BiomarkerFeatures

try:
    import cv2
    import mediapipe as mp
    _MEDIAPIPE_OK = True
except Exception:  # pragma: no cover - dependências opcionais em dev
    _MEDIAPIPE_OK = False


class FeatureExtractor:
    """Captura frames da webcam e produz um BiomarkerFeatures por sessão."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._series: dict[str, list[float]] = defaultdict(list)
        if _MEDIAPIPE_OK:
            self._mp_face = mp.solutions.face_mesh.FaceMesh(
                refine_landmarks=True, max_num_faces=1)
            self._mp_pose = mp.solutions.pose.Pose()
            self._mp_hands = mp.solutions.hands.Hands(max_num_hands=2)

    def available(self) -> bool:
        return _MEDIAPIPE_OK

    def capture(self, duration_s: float = 30.0) -> BiomarkerFeatures:
        """Captura por `duration_s` segundos e devolve os biomarcadores agregados."""
        if not _MEDIAPIPE_OK:
            raise RuntimeError(
                "OpenCV/MediaPipe indisponíveis. Instale opencv-python e mediapipe.")

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir a webcam {self.camera_index}.")

        self._series.clear()
        t0 = time.monotonic()
        frames = 0
        try:
            while time.monotonic() - t0 < duration_s:
                ok, frame = cap.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self._process_frame(rgb)
                frames += 1
        finally:
            cap.release()

        elapsed = max(time.monotonic() - t0, 1e-6)
        return self._aggregate(frames=frames, duration_s=elapsed)

    # -- processamento por frame -------------------------------------------------

    def _process_frame(self, rgb) -> None:
        face = self._mp_face.process(rgb)
        pose = self._mp_pose.process(rgb)
        hands = self._mp_hands.process(rgb)

        if face.multi_face_landmarks:
            lm = face.multi_face_landmarks[0].landmark
            self._series["face_asym"].append(self._facial_asymmetry(lm))
            self._series["ear"].append(self._eye_aspect_ratio(lm))
        if hands.multi_hand_landmarks:
            wrist = hands.multi_hand_landmarks[0].landmark[0]
            self._series["hand_x"].append(wrist.x)
            self._series["hand_y"].append(wrist.y)
        if pose.pose_landmarks:
            nose = pose.pose_landmarks.landmark[0]
            self._series["body_x"].append(nose.x)
            self._series["body_y"].append(nose.y)

    # -- cálculos de marcadores --------------------------------------------------

    @staticmethod
    def _facial_asymmetry(lm) -> float:
        """Assimetria facial via distância dos cantos da boca ao eixo central."""
        left, right, center = lm[61], lm[291], lm[1]
        dl = abs(left.x - center.x)
        dr = abs(right.x - center.x)
        return abs(dl - dr) / max(dl + dr, 1e-6)

    @staticmethod
    def _eye_aspect_ratio(lm) -> float:
        """EAR aproximado do olho esquerdo para detecção de piscadas."""
        top, bottom, l, r = lm[159], lm[145], lm[33], lm[133]
        v = abs(top.y - bottom.y)
        h = abs(l.x - r.x)
        return v / max(h, 1e-6)

    def _dominant_freq(self, key: str, fps: float) -> tuple[float, float]:
        """Frequência dominante (Hz) e amplitude de uma série via FFT."""
        s = np.asarray(self._series.get(key, []), dtype=float)
        if s.size < 8:
            return 0.0, 0.0
        s = s - s.mean()
        spec = np.abs(np.fft.rfft(s))
        freqs = np.fft.rfftfreq(s.size, d=1.0 / max(fps, 1e-6))
        idx = int(np.argmax(spec[1:]) + 1)
        return float(freqs[idx]), float(s.std())

    def _aggregate(self, frames: int, duration_s: float) -> BiomarkerFeatures:
        fps = frames / duration_s
        hand_hz, hand_amp = self._dominant_freq("hand_x", fps)
        head_hz, _ = self._dominant_freq("body_x", fps)

        ear = np.asarray(self._series.get("ear", []), dtype=float)
        blinks = int(np.sum(np.diff((ear < 0.18).astype(int)) == 1)) if ear.size else 0
        blink_rate = blinks / (duration_s / 60.0) if duration_s else 0.0

        asym = np.asarray(self._series.get("face_asym", []), dtype=float)
        gaze = float(np.std(self._series.get("body_x", [0]))) if frames else 0.0
        body = float(np.std(self._series.get("body_x", [0])) +
                     np.std(self._series.get("body_y", [0]))) if frames else 0.0

        return BiomarkerFeatures(
            duration_s=duration_s,
            frames=frames,
            fps=fps,
            tremor_hand_hz=hand_hz,
            tremor_hand_amplitude=hand_amp,
            tremor_head_hz=head_hz,
            blink_rate_per_min=blink_rate,
            gaze_dispersion=gaze,
            facial_asymmetry=float(asym.mean()) if asym.size else 0.0,
            body_movement_index=body,
            postural_sway=body,
            time_series={k: list(v) for k, v in self._series.items()},
        )
