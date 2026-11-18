"""Reproducible WDBC breast-cancer classification experiment.

Positive class: malignant (1). Negative class: benign (0).
Hyperparameter sensitivity is evaluated with stratified 5-fold CV on the
training split only. The hold-out test set is used once for final evaluation.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import make_scorer

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"
MODELS = ROOT / "models"
SEED = 42
TEST_SIZE = 0.20
N_SPLITS = 5
N_FEATURES = 20

METRICS = ["accuracy", "precision", "sensitivity", "f1", "specificity", "roc_auc"]
METRIC_LABELS = {
    "accuracy": "Accuracy",
    "precision": "Precision",
    "sensitivity": "Sensitivity / Recall",
    "f1": "F1-score",
    "specificity": "Specificity",
    "roc_auc": "ROC-AUC",
}


def specificity_score(y_true, y_pred) -> float:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    denom = tn + fp
    return float(tn / denom) if denom else 0.0


def make_pipeline(estimator, scale: bool) -> Pipeline:
    steps = [("feature_selection", SelectKBest(score_func=f_classif, k=N_FEATURES))]
    if scale:
        steps.append(("scaler", StandardScaler()))
    steps.append(("classifier", estimator))
    return Pipeline(steps)


def get_configurations():
    """Return six controlled hyperparameter settings for every algorithm."""
    specs = {}
    specs["Naive Bayes"] = {
        "parameter": "var_smoothing",
        "description": "GaussianNB.var_smoothing",
        "values": [1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7],
        "labels": ["1e-12", "1e-11", "1e-10", "1e-9", "1e-8", "1e-7"],
        "scale": True,
        "factory": lambda v: GaussianNB(var_smoothing=v),
    }
    specs["KNN"] = {
        "parameter": "n_neighbors",
        "description": "KNeighborsClassifier.n_neighbors (k)",
        "values": [1, 3, 5, 7, 9, 11],
        "labels": ["1", "3", "5", "7", "9", "11"],
        "scale": True,
        "factory": lambda v: KNeighborsClassifier(n_neighbors=v, weights="distance", metric="minkowski", p=2),
    }
    specs["Decision Tree"] = {
        "parameter": "max_depth",
        "description": "DecisionTreeClassifier.max_depth",
        "values": [1, 2, 3, 4, 6, 8],
        "labels": ["1", "2", "3", "4", "6", "8"],
        "scale": False,
        "factory": lambda v: DecisionTreeClassifier(max_depth=v, criterion="gini", random_state=SEED),
    }
    specs["Random Forest"] = {
        "parameter": "n_estimators",
        "description": "RandomForestClassifier.n_estimators",
        "values": [10, 25, 50, 100, 150, 200],
        "labels": ["10", "25", "50", "100", "150", "200"],
        "scale": False,
        "factory": lambda v: RandomForestClassifier(n_estimators=v, random_state=SEED, n_jobs=1),
    }
    specs["SVM"] = {
        "parameter": "C",
        "description": "SVC.C (RBF kernel)",
        "values": [0.01, 0.1, 1, 10, 100, 1000],
        "labels": ["0.01", "0.1", "1", "10", "100", "1000"],
        "scale": True,
        "factory": lambda v: SVC(C=v, kernel="rbf", gamma="scale", probability=True, random_state=SEED),
    }
    specs["Logistic Regression"] = {
        "parameter": "C",
        "description": "LogisticRegression.C (inverse regularization)",
        "values": [0.001, 0.01, 0.1, 1, 10, 100],
        "labels": ["0.001", "0.01", "0.1", "1", "10", "100"],
        "scale": True,
        "factory": lambda v: LogisticRegression(C=v, solver="liblinear", max_iter=3000, random_state=SEED),
    }
    specs["ANN"] = {
        "parameter": "hidden_layer_sizes",
        "description": "MLPClassifier.hidden_layer_sizes",
        "values": [(8,), (16,), (32,), (16, 8), (32, 16), (64, 32)],
        "labels": ["(8)", "(16)", "(32)", "(16,8)", "(32,16)", "(64,32)"],
        "scale": True,
        "factory": lambda v: MLPClassifier(
            hidden_layer_sizes=v, activation="relu", solver="adam", alpha=0.0001,
            learning_rate_init=0.001, max_iter=1600, early_stopping=True,
            n_iter_no_change=25, validation_fraction=0.15, random_state=SEED,
        ),
    }
    return specs


def make_scoring():
    return {
        "accuracy": "accuracy",
        "precision": make_scorer(precision_score, zero_division=0),
        "sensitivity": "recall",
        "f1": "f1",
        "specificity": make_scorer(specificity_score),
        "roc_auc": "roc_auc",
    }


def metric_values(y_true, y_pred, y_score):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "sensitivity": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "specificity": float(specificity_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
    }


def save_sensitivity_plot(name: str, spec: dict, df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.4, 5.7), dpi=180)
    x = np.arange(len(spec["labels"]))
    markers = ["o", "s", "^", "D", "P", "X"]
    for metric, marker in zip(METRICS, markers):
        ax.plot(x, df[f"mean_{metric}"], marker=marker, linewidth=2.0,
                markersize=5.5, label=METRIC_LABELS[metric])
    ax.set_xticks(x, spec["labels"])
    ax.set_ylim(0.55, 1.02)
    ax.set_ylabel("Mean 5-fold cross-validation score")
    ax.set_xlabel(spec["parameter"])
    ax.set_title(f"{name}: six-metric sensitivity analysis", fontsize=13, weight="bold")
    ax.grid(True, alpha=0.28, linestyle="--")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.34), frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    path = FIGURES / f"sensitivity_{name.lower().replace(' ', '_')}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main():
    for p in [FIGURES, TABLES, MODELS, ROOT / "data"]:
        p.mkdir(parents=True, exist_ok=True)

    bundle = load_breast_cancer(as_frame=True)
    X = bundle.data.copy()
    # sklearn encodes malignant=0 and benign=1; invert so malignant is the positive class.
    y = (bundle.target == 0).astype(int)
    y.name = "malignant_positive"

    df_data = X.copy()
    df_data["Diagnosis"] = np.where(y == 1, "Malignant", "Benign")
    df_data.to_csv(ROOT / "data" / "wdbc_dataset.csv", index=False)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED
    )
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    scoring = make_scoring()
    specs = get_configurations()

    sensitivity_summaries = {}
    best_models = {}
    best_rows = []
    test_predictions = pd.DataFrame(index=y_test.index)
    test_predictions["true_label"] = np.where(y_test == 1, "Malignant", "Benign")
    fitted_for_roc = {}

    for name, spec in specs.items():
        rows = []
        for value, label in zip(spec["values"], spec["labels"]):
            pipe = make_pipeline(spec["factory"](value), spec["scale"])
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ConvergenceWarning)
                cv_result = cross_validate(
                    pipe, X_train, y_train, cv=cv, scoring=scoring,
                    return_train_score=False, n_jobs=1, error_score="raise"
                )
            row = {"parameter_value": label}
            for metric in METRICS:
                scores = cv_result[f"test_{metric}"]
                row[f"mean_{metric}"] = float(np.mean(scores))
                row[f"std_{metric}"] = float(np.std(scores, ddof=1))
            row["mean_fit_time"] = float(np.mean(cv_result["fit_time"]))
            rows.append(row)

        sens_df = pd.DataFrame(rows)
        # Primary selection criterion is malignant sensitivity; F1 breaks ties.
        best_idx = sens_df.sort_values(["mean_sensitivity", "mean_f1", "mean_roc_auc"], ascending=False).index[0]
        best_value = spec["values"][int(best_idx)]
        best_label = spec["labels"][int(best_idx)]

        final_pipe = make_pipeline(spec["factory"](best_value), spec["scale"])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            final_pipe.fit(X_train, y_train)
        pred = final_pipe.predict(X_test)
        if hasattr(final_pipe, "predict_proba"):
            score = final_pipe.predict_proba(X_test)[:, 1]
        else:
            raw = final_pipe.decision_function(X_test)
            score = (raw - raw.min()) / (raw.max() - raw.min() + 1e-12)
        final_metrics = metric_values(y_test, pred, score)
        cm = confusion_matrix(y_test, pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        row = {
            "algorithm": name,
            "selected_parameter": spec["parameter"],
            "selected_value": best_label,
            "cv_sensitivity": sens_df.loc[best_idx, "mean_sensitivity"],
            "cv_f1": sens_df.loc[best_idx, "mean_f1"],
            **{f"test_{k}": v for k, v in final_metrics.items()},
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        }
        best_rows.append(row)
        best_models[name] = final_pipe
        fitted_for_roc[name] = (y_test, score)
        test_predictions[f"{name}_prediction"] = np.where(pred == 1, "Malignant", "Benign")

        safe_name = name.lower().replace(" ", "_")
        sens_df.insert(0, "algorithm", name)
        sens_df.to_csv(TABLES / f"sensitivity_{safe_name}.csv", index=False)
        sensitivity_summaries[name] = sens_df
        save_sensitivity_plot(name, spec, sens_df)
        joblib.dump(final_pipe, MODELS / f"{safe_name}.joblib")

    summary = pd.DataFrame(best_rows).sort_values("test_roc_auc", ascending=False)
    summary.to_csv(TABLES / "model_comparison_test.csv", index=False)
    test_predictions.to_csv(TABLES / "test_predictions.csv", index_label="sample_index")
    joblib.dump(best_models, MODELS / "all_best_models.joblib")

    # Test-set comparison chart (kept distinct from CV tuning charts).
    compare_metrics = ["accuracy", "sensitivity", "specificity", "f1", "roc_auc"]
    fig, ax = plt.subplots(figsize=(11.5, 6.3), dpi=180)
    xpos = np.arange(len(summary))
    width = 0.15
    for i, metric in enumerate(compare_metrics):
        ax.bar(xpos + (i - 2) * width, summary[f"test_{metric}"], width=width,
               label=METRIC_LABELS[metric])
    ax.set_xticks(xpos, summary["algorithm"], rotation=20, ha="right")
    ax.set_ylim(0.65, 1.02)
    ax.set_ylabel("Hold-out test score")
    ax.set_title("Final hold-out test comparison (best CV setting per model)", weight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.legend(ncol=3, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.31))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(FIGURES / "test_model_comparison.png", bbox_inches="tight")
    plt.close(fig)

    # ROC curves for all final models on the same untouched test split.
    fig, ax = plt.subplots(figsize=(8.6, 7.2), dpi=180)
    for name, (yt, score) in fitted_for_roc.items():
        fpr, tpr, _ = roc_curve(yt, score)
        auc = roc_auc_score(yt, score)
        ax.plot(fpr, tpr, linewidth=2, label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.2, label="Random classifier")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.set_xlabel("False Positive Rate (1 - Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity)")
    ax.set_title("ROC curves on the hold-out test set", weight="bold")
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.legend(loc="lower right", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(FIGURES / "roc_curves_test.png", bbox_inches="tight")
    plt.close(fig)

    # Confusion matrix panels for each final model.
    names = list(specs.keys())
    fig, axes = plt.subplots(2, 4, figsize=(13.2, 7.2), dpi=180)
    for ax, name in zip(axes.flat, names):
        r = summary[summary.algorithm == name].iloc[0]
        cm = np.array([[r.TN, r.FP], [r.FN, r.TP]])
        ax.imshow(cm, interpolation="nearest", cmap="Blues")
        ax.set_title(name, fontsize=10, weight="bold")
        ax.set_xticks([0, 1], ["Benign", "Malignant"], rotation=20)
        ax.set_yticks([0, 1], ["Benign", "Malignant"])
        ax.set_xlabel("Predicted", fontsize=8)
        ax.set_ylabel("Actual", fontsize=8)
        threshold = cm.max() / 2 if cm.max() else 0
        for (i, j), val in np.ndenumerate(cm):
            ax.text(j, i, str(int(val)), ha="center", va="center",
                    color="white" if val > threshold else "black", fontsize=11, weight="bold")
    axes.flat[-1].axis("off")
    fig.suptitle("Confusion matrices - hold-out test set", fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "confusion_matrices_test.png", bbox_inches="tight")
    plt.close(fig)

    # Machine-readable run metadata.
    metadata = {
        "dataset": "Wisconsin Breast Cancer Diagnostic (WDBC), scikit-learn bundled copy",
        "samples": int(X.shape[0]), "original_features": int(X.shape[1]),
        "selected_features": N_FEATURES, "positive_class": "Malignant",
        "negative_class": "Benign", "split": {"test_size": TEST_SIZE, "random_state": SEED, "stratified": True},
        "cross_validation": {"type": "StratifiedKFold", "n_splits": N_SPLITS, "shuffle": True, "random_state": SEED},
        "selection_rule": "Highest mean CV sensitivity; ties broken by F1 then ROC-AUC",
        "algorithms": list(specs.keys()),
    }
    (RESULTS / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(summary[["algorithm", "selected_value", "test_accuracy", "test_sensitivity", "test_specificity", "test_f1", "test_roc_auc"]].to_string(index=False))
    print(f"\nSaved outputs under: {ROOT}")

if __name__ == "__main__":
    main()
