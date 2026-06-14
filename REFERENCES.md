# Fundamentação científica dos biomarcadores

As técnicas implementadas são baseadas em literatura revisada por pares de alto
impacto. **Ressalva:** os limiares de decisão ainda são heurísticos (não calibrados
com dataset clínico). Ferramenta de triagem/pesquisa — não diagnóstico.

## rPPG — frequência cardíaca e VFC sem contato (`app/vision/rppg.py`)
- Wang, den Brinker, Stuijk, de Haan. *Algorithmic Principles of Remote PPG.*
  IEEE Transactions on Biomedical Engineering, 2017. **(método POS, implementado)**
- de Haan & Jeanne. *Robust pulse rate from chrominance-based rPPG.* IEEE TBME, 2013.
- Poh, McDuff, Picard. *Non-contact, automated cardiac pulse measurements using
  video imaging and blind source separation.* Optics Express, 2010.

## Métricas oculomotoras (`app/vision/oculomotor.py`)
- Anderson & MacAskill. *Eye movements in patients with neurodegenerative
  disorders.* Nature Reviews Neurology, 2013.
- Bahill, Clark, Stark. *The main sequence, a tool for studying human eye
  movements.* Mathematical Biosciences, 1975.
- Crawford et al. *Inhibitory control of saccadic eye movements and cognitive
  impairment in Alzheimer's disease.* Biological Psychiatry, 2005.
- BCEA (estabilidade de fixação): Steinman, 1965; Castet & Crossland, 2012.

## Hipomimia facial e estereotipias (`app/vision/motor_face.py`)
- Bandini et al. *Analysis of facial expressions in Parkinson's disease through
  video-based automatic methods.* Journal of Neuroscience Methods, 2017.
- Ekman & Friesen. *Facial Action Coding System (FACS),* 1978.
- Baltrušaitis et al. *OpenFace 2.0: Facial Behavior Analysis Toolkit.* IEEE FG, 2018.
- Goodwin et al. *Automated detection of stereotypical motor movements.*
  Journal of Autism and Developmental Disorders, 2011.

## Landmarks faciais de alta precisão (`app/vision/face_landmarker.py`)
- MediaPipe **Face Landmarker** (Google): 478 landmarks 3D + **52 blendshapes**
  (intensidades de Action Units medidas pela rede) + matriz de pose da cabeça.
- Kartynnik et al. *Real-time Facial Surface Geometry from Monocular Video on
  Mobile GPUs*, CVPR Workshops, 2019.
- Os blendshapes substituem proxies geométricos no cálculo de hipomimia,
  microexpressões, assimetria facial, piscar e olhar (`blendshape_features.py`),
  com fallback automático para a malha geométrica quando o modelo não está presente.

## Processamento de sinal (`app/vision/signal.py`)
- Casiez, Roussel, Vogel. *1€ Filter: a simple speed-based low-pass filter.*
  ACM CHI, 2012. (One-Euro)
- Welch. *The use of FFT for the estimation of power spectra.* IEEE Trans. Audio
  Electroacoustics, 1967. (PSD robusta de tremor)

## Marcadores por transtorno (literatura de apoio)
- **TEA:** Jones & Klin. *Attention to eyes is present but in decline in 2–6-month-old
  infants later diagnosed with autism.* Nature, 2013. (contato visual / fixação ocular)
- **Síndrome de Down:** Gurovich et al. *Identifying facial phenotypes of genetic
  disorders using deep learning.* Nature Medicine, 2019. (fenótipo facial — o
  indicador dinâmico aqui é apenas auxiliar; confirmação exige morfologia/genética)
