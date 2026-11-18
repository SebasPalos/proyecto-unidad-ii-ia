# ¡Convence a la IA!

Juego arcade de detección de emociones con YOLO11n. Elige una emoción, actúala frente a la
webcam y haz que la IA te crea durante 30 segundos. Entre más tiempo la sostengas, más sube
tu multiplicador.

## Instalación

PyTorch con CUDA se instala aparte y **antes** que lo demás, para usar la GPU:

```bash
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
```

## Jugar

```bash
python main.py            # con el modelo entrenado (models/best.pt)
python main.py --fake     # modo prueba: simula al modelo con el teclado (1-6, 0 = sin rostro)
python main.py --gris     # cámara en escala de grises (también con G en el menú)
python main.py --camera 1 # otra webcam
```

Controles: flechas para elegir, Enter para jugar, Esc para volver al menú o salir.

Durante la ronda el puntaje se ve en dos lugares a la vez: en el panel derecho y en un
marcador flotante que sigue tu cabeza (`+000` / `-000` y el multiplicador `x1`). Los dos leen
el mismo valor. Cada vez que el puntaje cambia suena un efecto: agudo al sumar, grave al restar.

## Modelo

`models/best.pt` ya viene entrenado (100 épocas, 640 px). Métricas en el conjunto de prueba
(`models/metricas.txt`): mAP50 0.862, precisión 0.848, recall 0.740.

## Reentrenar

El dataset no está en el repositorio porque pesa 1.1 GB. Descárgalo de Roboflow en formato
YOLOv8 desde la URL que trae `datasets/emociones/data.yaml` y descomprímelo en
`datasets/emociones/` (deben quedar las carpetas `train/`, `valid/` y `test/`).

```bash
python train.py --epochs 100
```

## Pruebas

```bash
python -m pytest
```

## Estructura

| Ruta | Qué hay |
|---|---|
| `emotion_game/` | Lógica del juego: puntaje, cámara, detector, ranking, estilo arcade (`retro.py`), marcador flotante (`score_marker.py`) y sonidos (`sound.py`) |
| `tests/` | Pruebas con pytest |
| `models/` | Modelo entrenado y métricas |
| `lona/` | Diseño de la lona (HTML editable, PDF 100 × 100 cm y JPG 150 dpi) |
| `manual_roboflow_yolo.pdf` | Manual de Roboflow + YOLO |
