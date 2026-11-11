"""Evaluasi mesin analisis pada himpunan uji berlabel (data/eval_set.csv).

CATATAN KEJUJURAN METODOLOGI
    Himpunan uji ditulis oleh pengembang yang sama dengan pembuat kamus isyarat,
    dan beberapa kesalahan yang ditemukan di sana dipakai untuk memperbaiki kamus.
    Jadi angka di sini adalah uji kewajaran (sanity check) - BUKAN klaim akurasi
    di dunia nyata. Kolom `kesulitan` memisahkan kalimat yang mengandung isyarat
    kata jelas ("mudah") dari kalimat tanpa isyarat eksplisit ("sulit"), supaya
    keterbatasan pendekatan berbasis kamus terlihat apa adanya.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from . import constants as C
from .analyzer import analyze_text
from .data import EVAL_PATH
from .text_utils import safe_text


@lru_cache(maxsize=1)
def load_eval_set() -> pd.DataFrame:
    df = pd.read_csv(EVAL_PATH, encoding="utf-8-sig", dtype=str)
    df["text"] = df["text"].map(safe_text)
    df["kesulitan"] = df["kesulitan"].fillna("mudah")
    return df


def _prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate(threshold: float = C.BINARY_RISK_THRESHOLD) -> dict:
    """Jalankan analyzer pada himpunan uji dan hitung metrik."""
    df = load_eval_set().copy()
    results = [analyze_text(t) for t in df["text"]]
    df["risk"] = [r["risk"] for r in results]
    df["pred_label"] = [r["label"] for r in results]
    df["true_risky"] = df["label"].isin(C.RISK_CATEGORIES)
    df["pred_risky"] = df["risk"] >= threshold

    tp = int((df["true_risky"] & df["pred_risky"]).sum())
    fp = int((~df["true_risky"] & df["pred_risky"]).sum())
    fn = int((df["true_risky"] & ~df["pred_risky"]).sum())
    tn = int((~df["true_risky"] & ~df["pred_risky"]).sum())
    overall = _prf(tp, fp, fn)
    overall["accuracy"] = (tp + tn) / len(df) if len(df) else 0.0

    by_difficulty = {}
    for diff, g in df.groupby("kesulitan"):
        gtp = int((g["true_risky"] & g["pred_risky"]).sum())
        gfp = int((~g["true_risky"] & g["pred_risky"]).sum())
        gfn = int((g["true_risky"] & ~g["pred_risky"]).sum())
        by_difficulty[diff] = {"n": len(g), "tp": gtp, "fp": gfp, "fn": gfn, **_prf(gtp, gfp, gfn)}

    # akurasi kategori untuk yang terdeteksi berisiko dan memang berisiko
    hit = df[df["true_risky"] & df["pred_risky"]]
    cat_acc = float((hit["label"] == hit["pred_label"]).mean()) if len(hit) else 0.0

    per_cat = []
    for cat in C.ALL_LABELS:
        g = df[df["label"] == cat]
        if not len(g):
            continue
        if cat in C.RISK_CATEGORIES:
            ok = int((g["pred_risky"]).sum())
            per_cat.append({"kategori": cat, "jumlah": len(g), "terdeteksi": ok, "ukuran": "recall",
                            "nilai": ok / len(g)})
        else:
            ok = int((~g["pred_risky"]).sum())
            per_cat.append({"kategori": cat, "jumlah": len(g), "terdeteksi": ok, "ukuran": "tidak salah tandai",
                            "nilai": ok / len(g)})

    errors = df[df["true_risky"] != df["pred_risky"]].copy()
    errors["jenis"] = errors.apply(lambda r: "Terlewat (false negative)" if r["true_risky"] else "Salah tandai (false positive)", axis=1)
    errors = errors[["id", "jenis", "kesulitan", "label", "pred_label", "risk", "text"]].reset_index(drop=True)

    return {
        "n": len(df), "threshold": float(threshold),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "overall": overall, "by_difficulty": by_difficulty, "category_accuracy": cat_acc,
        "per_category": pd.DataFrame(per_cat), "errors": errors, "detail": df,
    }
