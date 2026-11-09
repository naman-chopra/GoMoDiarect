#!/usr/bin/env python3
"""
GoMoDiarect: Model Evaluation & Metric Verification Script

Evaluates trained Diabetic Retinopathy classification/regression models (.h5)
on holdout test images and computes standard clinical metrics:
- Quadratic Weighted Kappa (QWK)
- Classification Accuracy
- Per-class Precision, Recall, F1-Score
- Confusion Matrix

Usage:
    python evaluate.py --model models/resnet_model.h5 --labels test.csv --images test_images/
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, classification_report, confusion_matrix

# Ensure server package imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from preprocess import DR_CLASSES, preprocess_retinal_image


def load_inference_model(model_path):
    """Load Keras model weights with custom layer handling."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found at: {model_path}")
    
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    
    try:
        # Attempt standard load
        model = load_model(model_path, compile=False)
    except Exception as e:
        print(f"[WARN] Standard load failed ({e}), attempting custom object resolution...")
        custom_objects = {}
        try:
            import keras_radam
            custom_objects['RAdam'] = keras_radam.RAdam
        except ImportError:
            pass
        model = load_model(model_path, custom_objects=custom_objects, compile=False)
        
    return model


def evaluate_dataset(model, df, img_dir, img_size=512, id_col="id_code", label_col="diagnosis"):
    """
    Run inference over a DataFrame of images and evaluate against ground truth labels.
    """
    y_true = []
    y_pred = []
    skipped = 0
    
    print(f"[*] Commencing evaluation over {len(df)} samples...")
    for idx, row in df.iterrows():
        img_id = str(row[id_col])
        if not (img_id.endswith(".png") or img_id.endswith(".jpg") or img_id.endswith(".jpeg")):
            img_file = f"{img_id}.png"
            if not os.path.exists(os.path.join(img_dir, img_file)):
                img_file = f"{img_id}.jpg"
        else:
            img_file = img_id
            
        full_path = os.path.join(img_dir, img_file)
        if not os.path.exists(full_path):
            skipped += 1
            continue
            
        try:
            _, tensor = preprocess_retinal_image(full_path, img_size=img_size)
            raw_pred = model.predict(tensor, verbose=0)
            
            if raw_pred.shape[-1] == 1:
                # Continuous regression output
                pred_grade = int(np.clip(np.round(raw_pred[0][0]), 0, 4))
            else:
                pred_grade = int(np.argmax(raw_pred[0]))
                
            y_true.append(int(row[label_col]))
            y_pred.append(pred_grade)
        except Exception as err:
            print(f"[!] Error processing {full_path}: {err}")
            skipped += 1

    if skipped > 0:
        print(f"[!] Skipped {skipped} files due to missing paths or read errors.")
        
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    # Calculate metrics
    qwk = cohen_kappa_score(y_true, y_pred, weights="quadratic")
    acc = np.mean(y_true == y_pred)
    conf_mat = confusion_matrix(y_true, y_pred, labels=list(range(5)))
    
    target_names = [f"Grade {i} ({DR_CLASSES[i]['name']})" for i in range(5)]
    class_report = classification_report(y_true, y_pred, labels=list(range(5)), target_names=target_names, zero_division=0)
    
    return {
        "qwk": qwk,
        "accuracy": acc,
        "confusion_matrix": conf_mat,
        "report": class_report,
        "total_evaluated": len(y_true)
    }


def main():
    parser = argparse.ArgumentParser(description="GoMoDiarect Model Evaluation Utility")
    parser.add_argument("--model", type=str, required=True, help="Path to trained .h5 model checkpoint")
    parser.add_argument("--labels", type=str, required=True, help="Path to ground truth labels CSV")
    parser.add_argument("--images", type=str, required=True, help="Directory containing fundus image files")
    parser.add_argument("--img_size", type=int, default=512, help="Input dimension for resizing (default: 512)")
    parser.add_argument("--id_col", type=str, default="id_code", help="Column name for image identifiers")
    parser.add_argument("--label_col", type=str, default="diagnosis", help="Column name for severity grade (0-4)")
    parser.add_argument("--out_csv", type=str, default=None, help="Optional output path to save per-image predictions")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("GoMoDiarect: Offline Model Evaluation")
    print("=" * 70)
    print(f"Model Path    : {args.model}")
    print(f"Labels CSV    : {args.labels}")
    print(f"Image Directory: {args.images}")
    
    df = pd.read_csv(args.labels)
    model = load_inference_model(args.model)
    
    results = evaluate_dataset(
        model=model,
        df=df,
        img_dir=args.images,
        img_size=args.img_size,
        id_col=args.id_col,
        label_col=args.label_col
    )
    
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Total Evaluated Samples : {results['total_evaluated']}")
    print(f"Quadratic Weighted Kappa: {results['qwk']:.4f}")
    print(f"Multi-class Accuracy    : {results['accuracy'] * 100:.2f}%\n")
    print("Classification Report:")
    print(results['report'])
    print("\nConfusion Matrix (Rows: Ground Truth, Cols: Predicted):")
    print(results['confusion_matrix'])
    print("=" * 70)


if __name__ == "__main__":
    main()
