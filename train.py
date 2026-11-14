"""Entrena YOLO11n con el dataset de emociones, localmente y sin internet.

    python train.py                 entrena 50 épocas con datasets/emociones
    python train.py --epochs 30     cambia el número de épocas
    python train.py --resume        continúa un entrenamiento interrumpido

Al terminar copia el mejor modelo a models/best.pt, lo evalúa con el conjunto de
prueba (test) y guarda las métricas en models/metricas.txt.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from emotion_game import config
from emotion_game.dataset_check import DatasetError, check_dataset


def parse_args():
    parser = argparse.ArgumentParser(description="Entrenar el detector de emociones.")
    parser.add_argument("--data", type=Path, default=config.DATASET_DIR, help="carpeta con data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16, help="bájalo a 8 si se acaba la memoria de la GPU")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--patience", type=int, default=15, help="épocas sin mejorar antes de detenerse")
    parser.add_argument("--name", default="emociones", help="nombre de la carpeta en runs/detect")
    parser.add_argument("--resume", action="store_true", help="continuar desde el último checkpoint")
    parser.add_argument("--runs", type=Path, default=config.RUNS_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=config.MODEL_PATH, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Ultralytics guarda y busca sus pesos auxiliares en "weights/" relativo a la carpeta actual
    os.chdir(config.PROJECT_DIR)

    try:
        report = check_dataset(args.data)
    except DatasetError as error:
        sys.exit(f"Dataset con problemas: {error}")
    print(f"Dataset OK: {report.counts}  clases: {report.names}")

    import torch
    from ultralytics import YOLO, settings

    settings.update({"sync": False})  # no enviar estadísticas de uso
    if torch.cuda.is_available():
        device = 0
        print(f"Entrenando en GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        print("AVISO: no se detectó GPU, el entrenamiento en CPU tardará muchísimo.")

    data_yaml = str(args.data / "data.yaml")
    if args.resume:
        last = args.runs / args.name / "weights" / "last.pt"
        if not last.exists():
            sys.exit(f"No hay entrenamiento que continuar en {last}")
        results = YOLO(str(last)).train(resume=True)
    else:
        results = YOLO(str(config.BASE_MODEL_PATH)).train(
            data=data_yaml,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            device=device,
            workers=4,
            project=str(args.runs),
            name=args.name,
            exist_ok=False,
        )

    best = Path(results.save_dir) / "weights" / "best.pt"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        shutil.copy2(args.out, args.out.with_name("best_anterior.pt"))
    shutil.copy2(best, args.out)
    print(f"Mejor modelo copiado a {args.out}")

    evaluate(args.out, data_yaml, args.imgsz, device, Path(results.save_dir))


def evaluate(model_path: Path, data_yaml: str, imgsz: int, device, run_dir: Path) -> None:
    """Evaluación final con el conjunto de prueba, que el modelo nunca vio al entrenar."""
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    metrics = model.val(data=data_yaml, split="test", imgsz=imgsz, device=device,
                        project=str(run_dir), name="test", exist_ok=True)
    box = metrics.box
    lines = [
        f"Modelo: {model_path}",
        f"Entrenamiento: {run_dir}",
        "",
        "Conjunto de prueba (test)",
        f"  mAP50:     {box.map50:.3f}",
        f"  mAP50-95:  {box.map:.3f}",
        f"  Precision: {box.mp:.3f}",
        f"  Recall:    {box.mr:.3f}",
        "",
        "mAP50 por emoción",
    ]
    for index, class_id in enumerate(box.ap_class_index):
        name = model.names[int(class_id)]
        lines.append(f"  {config.EMOTIONS.get(name, name):<10} {box.ap50[index]:.3f}")
    # La validación usa conf=0.001 para calcular el mAP, y con ese umbral la matriz de confusión
    # cuenta predicciones casi seguras de ser ruido. Se repite con el umbral que usa el juego.
    game_metrics = model.val(data=data_yaml, split="test", imgsz=imgsz, device=device,
                             conf=config.DETECTION_CONF, project=str(run_dir),
                             name="test_juego", exist_ok=True, verbose=False)
    matrix_path = Path(game_metrics.save_dir) / "confusion_matrix_normalized.png"
    lines += ["", f"Matriz de confusión (umbral del juego, conf={config.DETECTION_CONF}): {matrix_path}"]

    report = "\n".join(lines)
    print("\n" + report)
    model_path.with_name("metricas.txt").write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
