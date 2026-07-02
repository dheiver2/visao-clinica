# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller — gera o "Visão Clínica.app" autocontido (macOS).

    pyinstaller VisaoClinica.spec --noconfirm

Decisões de empacotamento:
* Embute `models/face_landmarker.task` → triagem facial funciona offline já na
  1ª execução, sem download.
* NÃO embute o GGUF do BitNet (~1.1 GB) por padrão — a narrativa do LLM é opt-in
  e o app baixa o modelo na 1ª vez para a área gravável do usuário. Para embutir
  mesmo assim, exporte BUNDLE_GGUF=1 antes do build.
* Exclui torch/transformers/accelerate/dask: são fallback opcional do BitNet
  (importados lazonly) e inflariam o bundle em ~2 GB.
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

PROJ = Path(os.getcwd())

# --- assets read-only embutidos ------------------------------------------------
datas = []
binaries = []

_face_task = PROJ / "models" / "face_landmarker.task"
if _face_task.exists():
    datas.append((str(_face_task), "models"))

if os.environ.get("BUNDLE_GGUF") == "1":
    for gguf in (PROJ / "models").rglob("*.gguf"):
        rel = gguf.parent.relative_to(PROJ)
        datas.append((str(gguf), str(rel)))

# MediaPipe precisa dos seus modelos/binários auxiliares.
datas += collect_data_files("mediapipe")
binaries += collect_dynamic_libs("mediapipe")

block_cipher = None

a = Analysis(
    ["run_app.py"],
    pathex=[str(PROJ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["app", "app.ui.main_window"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # matplotlib é dependência do mediapipe.solutions (drawing_utils) — NÃO excluir.
        "torch", "transformers", "accelerate", "dask", "distributed",
        "tkinter", "PyQt5", "PyQt6", "IPython", "pytest",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="VisaoClinica",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                       # app de janela (sem terminal)
    disable_windowed_traceback=False,
    argv_emulation=True,                 # permite abrir via Finder/arquivos
    target_arch=None,                    # arch da máquina de build
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="VisaoClinica",
)

_icon = Path("/tmp/VisaoClinica.icns")
app = BUNDLE(
    coll,
    name="Visão Clínica.app",
    icon=str(_icon) if _icon.exists() else None,
    bundle_identifier="br.com.visaoclinica.app",
    version="1.0",
    info_plist={
        "CFBundleName": "Visão Clínica",
        "CFBundleDisplayName": "Visão Clínica",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0",
        "NSHighResolutionCapable": True,
        "NSCameraUsageDescription":
            "O Visão Clínica usa a câmera para a triagem por visão "
            "computacional, processada 100% localmente.",
        "LSMinimumSystemVersion": "12.0",
    },
)
