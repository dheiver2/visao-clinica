"""Extração de biomarcadores a partir da webcam usando OpenCV + MediaPipe.

Pipeline: Webcam -> Face Mesh + Pose + Hands -> features agregadas.

A extração detalhada de cada marcador é organizada em métodos privados para
manter o pipeline legível. Onde o cálculo fino ainda não foi implementado,
o método retorna 0.0 e registra a série temporal correspondente para
processamento posterior (Dask).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict

import numpy as np

from . import blendshape_features, motor_face, oculomotor, signal, vitals
from .features import BiomarkerFeatures

try:
    import cv2
    import mediapipe as mp
    _MEDIAPIPE_OK = True
    _IMPORT_ERROR = None
except Exception as _e:  # pragma: no cover - dependências opcionais em dev
    _MEDIAPIPE_OK = False
    _IMPORT_ERROR = _e
    if os.environ.get("VISAOCLINICA_DEBUG"):
        import traceback
        traceback.print_exc()


class FeatureExtractor:
    """Captura frames da webcam e produz um BiomarkerFeatures por sessão."""

    def __init__(self, camera_index: int = 0, use_landmarker: bool = True):
        self.camera_index = camera_index
        self._series: dict[str, list[float]] = defaultdict(list)
        self._face_lm = None
        self._last_face = None
        if _MEDIAPIPE_OK:
            self._mp_face = mp.solutions.face_mesh.FaceMesh(
                refine_landmarks=True, max_num_faces=1)
            self._mp_pose = mp.solutions.pose.Pose()
            self._mp_hands = mp.solutions.hands.Hands(max_num_hands=2)
            # Face Landmarker de alta precisão (478 landmarks + 52 blendshapes/AUs).
            if use_landmarker:
                try:
                    from .face_landmarker import FaceLandmarker
                    fl = FaceLandmarker()
                    self._face_lm = fl if fl.available() else None
                except Exception:  # noqa: BLE001 - fallback p/ malha geométrica
                    self._face_lm = None

    def available(self) -> bool:
        return _MEDIAPIPE_OK

    def capture(self, duration_s: float = 30.0, on_frame=None,
                should_stop=None) -> BiomarkerFeatures:
        """Captura por `duration_s` segundos e devolve os biomarcadores agregados.

        on_frame(rgb, elapsed, duration): callback opcional por frame (ex.: preview
            ao vivo na UI). should_stop(): callable opcional; se retornar True,
            interrompe a captura antecipadamente (cancelamento pela UI).
        """
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
            while True:
                elapsed = time.monotonic() - t0
                if elapsed >= duration_s:
                    break
                if should_stop is not None and should_stop():
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self._process_frame(rgb)
                frames += 1
                if on_frame is not None:
                    on_frame(self._draw_overlay(rgb), elapsed, duration_s)
        finally:
            cap.release()

        elapsed = max(time.monotonic() - t0, 1e-6)
        return self._aggregate(frames=frames, duration_s=elapsed)

    def stream(self, on_frame, should_stop, analyze_flag,
               duration_s: float = 12.0, on_analysis=None, on_progress=None):
        """Mantém a webcam ATIVA continuamente, com preview ao vivo (overlay).

        on_frame(rgb): chamado a cada frame (já com a malha desenhada).
        should_stop(): encerra o streaming (fechar a janela).
        analyze_flag(): callable que retorna True quando o usuário pediu uma análise;
            ao detectar True, coleta `duration_s` segundos de biomarcadores, chama
            on_analysis(features) e volta a só transmitir. Repetível à vontade.
        on_progress(elapsed, total): progresso da janela de análise.
        """
        if not _MEDIAPIPE_OK:
            raise RuntimeError("OpenCV/MediaPipe indisponíveis.")
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir a webcam {self.camera_index}.")
        analyzing = False
        t0 = 0.0
        try:
            while not should_stop():
                ok, frame = cap.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                if not analyzing and analyze_flag():
                    analyzing = True
                    t0 = time.monotonic()
                    self._series.clear()

                if analyzing:
                    elapsed = time.monotonic() - t0
                    self._process_frame(rgb)
                    if on_progress:
                        on_progress(elapsed, duration_s)
                    if elapsed >= duration_s:
                        analyzing = False
                        feats = self._aggregate(frames=len(self._series.get("lum", [])) or 1,
                                                duration_s=max(elapsed, 1e-6))
                        if on_analysis:
                            on_analysis(feats)
                else:
                    # mantém o rosto detectado p/ o overlay mesmo fora da análise
                    self._last_face = self._mp_face.process(rgb).multi_face_landmarks
                    self._last_face = self._last_face[0] if self._last_face else None

                on_frame(self._draw_overlay(rgb))
        finally:
            cap.release()

    # -- processamento por frame -------------------------------------------------

    def _capture_guidance(self, rgb):
        """Feedback de enquadramento em tempo real (posição/luz/distância).

        Paridade com a UX de captura dos apps de vitais (Binah/Anura): orienta o
        usuário a se posicionar bem ANTES/DURANTE a análise, elevando a qualidade
        do sinal. Retorna (mensagem, cor_bgr, ok).
        """
        good = (60, 220, 140)     # verde
        warn = (80, 190, 255)     # âmbar
        bad = (108, 93, 255)      # vermelho
        if self._last_face is None:
            return "Rosto nao detectado — posicione-se na camera", bad, False
        xs = [p.x for p in self._last_face.landmark]
        ys = [p.y for p in self._last_face.landmark]
        fw = max(xs) - min(xs)
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        lum = float(rgb.mean())
        if fw < 0.22:
            return "Aproxime-se da camera", warn, False
        if fw > 0.75:
            return "Afaste-se um pouco", warn, False
        if abs(cx - 0.5) > 0.18 or abs(cy - 0.5) > 0.20:
            return "Centralize o rosto", warn, False
        if lum < 55:
            return "Ambiente escuro — melhore a iluminacao", warn, False
        if lum > 210:
            return "Muita luz — reduza o brilho/contraluz", warn, False
        return "Enquadramento otimo — pode analisar", good, True

    def _draw_overlay(self, rgb):
        """Desenha a malha de landmarks (tesselação) e a bounding box sobre o frame,
        para o preview ao vivo mostrar a análise acontecendo no usuário."""
        if not _MEDIAPIPE_OK:
            return rgb
        out = rgb.copy()
        h, w = out.shape[:2]

        # Banner de captura guiada (sempre visível, mesmo sem rosto).
        msg, color, ok = self._capture_guidance(rgb)
        cv2.rectangle(out, (0, 0), (w, 34), (18, 20, 26), -1)
        cv2.circle(out, (18, 17), 6, color, -1)
        cv2.putText(out, msg, (34, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    color, 1, cv2.LINE_AA)

        if self._last_face is None:
            return out
        mp.solutions.drawing_utils.draw_landmarks(
            image=out,
            landmark_list=self._last_face,
            connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(120, 230, 100), thickness=1))
        xs = [p.x for p in self._last_face.landmark]
        ys = [p.y for p in self._last_face.landmark]
        x0, y0 = int(min(xs) * w), int(min(ys) * h)
        x1, y1 = int(max(xs) * w), int(max(ys) * h)
        cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
        return out

    def _process_frame(self, rgb) -> None:
        self._series["lum"].append(float(rgb.mean()))   # luminância p/ qualidade
        face = self._mp_face.process(rgb)
        self._last_face = face.multi_face_landmarks[0] if face.multi_face_landmarks else None
        pose = self._mp_pose.process(rgb)
        hands = self._mp_hands.process(rgb)

        if face.multi_face_landmarks:
            lm = face.multi_face_landmarks[0].landmark
            self._series["face_asym"].append(self._facial_asymmetry(lm))
            self._series["ear"].append(self._eye_aspect_ratio(lm))
            self._sample_skin_roi(rgb, lm)   # cor da pele p/ rPPG
            # Ativações faciais (estilo blendshape) para microexpressões
            for name, val in self._facial_activations(lm).items():
                self._series[f"fa_{name}"].append(val)
            # Direção do olhar (íris normalizada na órbita) para saccades
            gx, gy = self._gaze_direction(lm)
            self._series["gaze_x"].append(gx)
            self._series["gaze_y"].append(gy)

        # Blendshapes (AUs) de alta precisão, quando disponível
        if self._face_lm is not None:
            res = self._face_lm.detect(np.ascontiguousarray(rgb))
            if res is not None and res.blendshapes:
                for name, score in res.blendshapes.items():
                    self._series[f"bs_{name}"].append(score)
        if hands.multi_hand_landmarks:
            wrist = hands.multi_hand_landmarks[0].landmark[0]
            self._series["hand_x"].append(wrist.x)
            self._series["hand_y"].append(wrist.y)
        if pose.pose_landmarks:
            nose = pose.pose_landmarks.landmark[0]
            self._series["body_x"].append(nose.x)
            self._series["body_y"].append(nose.y)

    # -- cálculos de marcadores --------------------------------------------------

    def _sample_skin_roi(self, rgb, lm) -> None:
        """Cor média de ROIs de pele (testa + bochechas) para rPPG."""
        h, w = rgb.shape[:2]
        # testa (10/151/9) e bochechas (50/280) — landmarks estáveis de pele
        pts = [lm[10], lm[151], lm[9], lm[50], lm[280]]
        xs = [int(min(max(p.x, 0), 1) * (w - 1)) for p in pts]
        ys = [int(min(max(p.y, 0), 1) * (h - 1)) for p in pts]
        x0, x1 = max(min(xs) - 8, 0), min(max(xs) + 8, w)
        y0, y1 = max(min(ys) - 8, 0), min(max(ys) + 8, h)
        if x1 <= x0 or y1 <= y0:
            return
        roi = rgb[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
        self._series["roi_r"].append(float(roi[0]))
        self._series["roi_g"].append(float(roi[1]))
        self._series["roi_b"].append(float(roi[2]))

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
        top, bottom, lx, r = lm[159], lm[145], lm[33], lm[133]
        v = abs(top.y - bottom.y)
        h = abs(lx.x - r.x)
        return v / max(h, 1e-6)

    @staticmethod
    def _facial_activations(lm) -> dict[str, float]:
        """Ativações faciais normalizadas pela largura interocular (escala-invariante).

        Proxies leves de unidades de ação usados para detectar microexpressões:
        elevação das sobrancelhas, abertura da boca e estiramento dos cantos (sorriso).
        """
        eye_l, eye_r = lm[33], lm[263]
        iod = max(((eye_l.x - eye_r.x) ** 2 + (eye_l.y - eye_r.y) ** 2) ** 0.5, 1e-6)
        brow_raise = (abs(lm[105].y - lm[159].y) + abs(lm[334].y - lm[386].y)) / (2 * iod)
        mouth_open = abs(lm[13].y - lm[14].y) / iod
        mouth_stretch = abs(lm[61].x - lm[291].x) / iod
        return {
            "brow_raise": brow_raise,
            "mouth_open": mouth_open,
            "mouth_stretch": mouth_stretch,
        }

    @staticmethod
    def _gaze_direction(lm) -> tuple[float, float]:
        """Posição da íris dentro da órbita, em [-1, 1] nos eixos x e y.

        Usa os centros de íris refinados (refine_landmarks=True: 468=esq, 473=dir)
        relativos aos cantos do olho. Alimenta a detecção de saccades.
        """
        def _eye(iris, inner, outer, top, bottom):
            cx = (inner.x + outer.x) / 2
            cy = (top.y + bottom.y) / 2
            w = max(abs(inner.x - outer.x), 1e-6)
            h = max(abs(top.y - bottom.y), 1e-6)
            return (iris.x - cx) / (w / 2), (iris.y - cy) / (h / 2)

        lx, ly = _eye(lm[468], lm[133], lm[33], lm[159], lm[145])
        rx, ry = _eye(lm[473], lm[362], lm[263], lm[386], lm[374])
        return (lx + rx) / 2, (ly + ry) / 2

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

        # --- Pré-processamento avançado: Hampel (outliers) + One-Euro (jitter) ---
        for key in ("hand_x", "hand_y", "body_x", "body_y", "gaze_x", "gaze_y"):
            s = self._series.get(key)
            if s and len(s) >= 8:
                self._series[key] = list(signal.one_euro(signal.hampel(s), fps))

        # --- Tremor por Welch na banda fisiológica 3–8 Hz (freq, amplitude, SNR) ---
        hand_hz, hand_amp, hand_snr = signal.dominant_freq(
            self._series.get("hand_x", []), fps, band=(3.0, 8.0))
        head_hz, _, _ = signal.dominant_freq(
            self._series.get("body_x", []), fps, band=(3.0, 8.0))

        ear = np.asarray(self._series.get("ear", []), dtype=float)
        blinks = int(np.sum(np.diff((ear < 0.18).astype(int)) == 1)) if ear.size else 0
        blink_rate = blinks / (duration_s / 60.0) if duration_s else 0.0

        asym = np.asarray(self._series.get("face_asym", []), dtype=float)
        body = float(np.std(self._series.get("body_x", [0])) +
                     np.std(self._series.get("body_y", [0]))) if frames else 0.0

        gaze_disp, saccade_rate = self._gaze_metrics(fps, duration_s)
        micro_rate, micro_int = self._microexpression_metrics(fps, duration_s)
        gaze_center, expr_amp, periodicity, mouth_open = self._composite_metrics(fps)

        # --- Qualidade do sinal: detecção de face × iluminação adequada ---
        face_rate = (len(self._series.get("ear", [])) / frames) if frames else 0.0
        bright_q = signal.quality_from_brightness(self._series.get("lum", []))
        sig_quality = float(max(0.0, min(1.0, face_rate)) * bright_q)

        # --- Biomarcadores avançados (literatura) ---
        roi = np.column_stack([self._series.get("roi_r", []),
                               self._series.get("roi_g", []),
                               self._series.get("roi_b", [])]) \
            if self._series.get("roi_g") else np.empty((0, 3))
        vit = vitals.compute(roi, fps)
        hr_bpm, hrv_ms, rppg_q = vit.heart_rate_bpm, vit.hrv_sdnn_ms, vit.quality
        bcea = oculomotor.fixation_bcea(self._series.get("gaze_x", []),
                                        self._series.get("gaze_y", []))
        ms_slope, _ = oculomotor.main_sequence_slope(
            self._series.get("gaze_x", []), self._series.get("gaze_y", []), fps)
        au = [np.asarray(v, float) for k, v in self._series.items()
              if k.startswith("fa_")]
        hypomimia = motor_face.hypomimia_index(au)
        stereotypy = motor_face.stereotypy_index(self._series.get("body_x", []), fps)
        facial_asym_value = float(asym.mean()) if asym.size else 0.0

        # --- Refinamento facial com blendshapes (AUs de alta precisão) ---
        bs = {k[3:]: v for k, v in self._series.items() if k.startswith("bs_")}
        if any(len(v) > 1 for v in bs.values()):
            blink_rate = blendshape_features.blink_rate(bs, fps, duration_s) or blink_rate
            facial_asym_value = blendshape_features.facial_asymmetry(bs)
            micro_rate, micro_int = blendshape_features.microexpression(bs, fps, duration_s)
            expr_amp = blendshape_features.expression_amplitude(bs)
            hypomimia = max(hypomimia, blendshape_features.hypomimia_index(bs))
            mouth_open = blendshape_features.mouth_open_ratio(bs)

        return BiomarkerFeatures(
            duration_s=duration_s,
            frames=frames,
            fps=fps,
            tremor_hand_hz=hand_hz,
            tremor_hand_amplitude=hand_amp,
            tremor_head_hz=head_hz,
            microexpression_rate=micro_rate,
            microexpression_intensity=micro_int,
            blink_rate_per_min=blink_rate,
            gaze_dispersion=gaze_disp,
            saccade_rate=saccade_rate,
            facial_asymmetry=facial_asym_value,
            body_movement_index=body,
            postural_sway=body,
            gaze_center_ratio=gaze_center,
            expression_amplitude=expr_amp,
            movement_periodicity=periodicity,
            mouth_open_ratio=mouth_open,
            signal_quality=sig_quality,
            face_detection_rate=float(max(0.0, min(1.0, face_rate))),
            tremor_snr=hand_snr,
            heart_rate_bpm=hr_bpm,
            hrv_sdnn_ms=hrv_ms,
            rppg_quality=rppg_q,
            respiration_bpm=vit.respiration_bpm,
            hrv_rmssd_ms=vit.hrv_rmssd_ms,
            hrv_pnn50=vit.hrv_pnn50,
            lf_hf_ratio=vit.lf_hf_ratio,
            stress_index=vit.stress_index,
            fixation_bcea=bcea,
            saccade_main_seq_slope=ms_slope,
            hypomimia_index=hypomimia,
            stereotypy_index=stereotypy,
            time_series={k: list(v) for k, v in self._series.items()},
        )

    def _composite_metrics(self, fps: float):
        """Marcadores para TEA/Parkinson/Alzheimer/Down.

        Retorna (gaze_center_ratio, expression_amplitude, movement_periodicity,
        mouth_open_ratio).
        """
        gx = np.asarray(self._series.get("gaze_x", []), dtype=float)
        gy = np.asarray(self._series.get("gaze_y", []), dtype=float)
        if gx.size:
            centered = (np.abs(gx) < 0.5) & (np.abs(gy) < 0.5)
            gaze_center = float(centered.mean())
        else:
            gaze_center = 0.0

        # Expressividade: amplitude média (desvio) dos canais de ativação facial.
        fa = [np.asarray(v, dtype=float) for k, v in self._series.items()
              if k.startswith("fa_") and len(v) > 1]
        expr_amp = float(np.mean([s.std() for s in fa])) if fa else 0.0

        # Periodicidade do movimento corporal: força do pico espectral dominante.
        body = np.asarray(self._series.get("body_x", []), dtype=float)
        if body.size >= 16:
            b = body - body.mean()
            spec = np.abs(np.fft.rfft(b))[1:]
            periodicity = float(spec.max() / (spec.sum() + 1e-9)) if spec.size else 0.0
        else:
            periodicity = 0.0

        mo = np.asarray(self._series.get("fa_mouth_open", []), dtype=float)
        mouth_open = float((mo > 0.12).mean()) if mo.size else 0.0
        return gaze_center, expr_amp, periodicity, mouth_open

    def _gaze_metrics(self, fps: float, duration_s: float) -> tuple[float, float]:
        """Dispersão do olhar e taxa de saccades/min a partir de gaze_x/gaze_y.

        Saccade = deslocamento angular do olhar acima de um limiar entre frames
        consecutivos (movimento balístico rápido).
        """
        gx = np.asarray(self._series.get("gaze_x", []), dtype=float)
        gy = np.asarray(self._series.get("gaze_y", []), dtype=float)
        if gx.size < 3:
            return 0.0, 0.0
        dispersion = float(np.hypot(gx.std(), gy.std()))
        speed = np.hypot(np.diff(gx), np.diff(gy)) * fps  # unidades-órbita/s
        saccades = int(np.sum(np.diff((speed > 3.0).astype(int)) == 1))
        rate = saccades / (duration_s / 60.0) if duration_s else 0.0
        return dispersion, rate

    def _microexpression_metrics(self, fps: float, duration_s: float) -> tuple[float, float]:
        """Taxa (eventos/min) e intensidade média de microexpressões.

        Detecta picos rápidos e breves (<~500 ms) nas ativações faciais — assinatura
        temporal de microexpressões — somando-os entre os canais (sobrancelha, boca).
        """
        channels = [k for k in self._series if k.startswith("fa_")]
        if not channels or fps <= 0:
            return 0.0, 0.0
        max_span = max(int(0.5 * fps), 1)  # janela de até ~500 ms
        events, intensities = 0, []
        for ch in channels:
            s = np.asarray(self._series[ch], dtype=float)
            if s.size < 5:
                continue
            base = float(np.median(s))
            mad = float(np.median(np.abs(s - base))) or 1e-6
            active = (np.abs(s - base) > 4 * mad).astype(int)
            # bordas de subida = início de um evento
            rises = np.where(np.diff(active) == 1)[0]
            for r in rises:
                seg = active[r + 1: r + 1 + max_span]
                if seg.size and seg.sum() <= max_span:  # transiente curto
                    events += 1
                    peak = r + 1 + int(np.argmax(np.abs(s[r + 1: r + 1 + max_span] - base)))
                    intensities.append(abs(s[min(peak, s.size - 1)] - base) / mad)
        rate = events / (duration_s / 60.0) if duration_s else 0.0
        intensity = float(np.mean(intensities)) if intensities else 0.0
        return rate, intensity
