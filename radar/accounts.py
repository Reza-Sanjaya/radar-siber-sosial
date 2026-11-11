"""Profil akun: skor perilaku tidak autentik (indikasi bot / jaringan terkoordinasi).

Penting: skor ini hanya *indikasi* untuk prioritas verifikasi manusia. Akun dikenali
melalui alias (pseudonim); tidak ada upaya mengungkap identitas pemilik akun.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import constants as C
from .coordination import peak_window_count

FACTOR_WEIGHTS = {
    "Laju unggah": 0.20,
    "Porsi konten kembar": 0.30,
    "Aktivitas 24 jam": 0.10,
    "Umur akun": 0.15,
    "Rasio mengikuti": 0.15,
    "Tautan/spam": 0.10,
}
STRONG = 65.0
WATCH = 40.0


def _hour_entropy(hours: np.ndarray) -> float:
    counts = np.bincount(hours.astype(int), minlength=24).astype(float)
    total = counts.sum()
    if total <= 0:
        return 0.0
    p = counts[counts > 0] / total
    return float(-(p * np.log(p)).sum() / math.log(24))


def _age_factor(age: float) -> float | None:
    if age is None or (isinstance(age, float) and math.isnan(age)):
        return None
    if age < 7:
        return 1.0
    if age < 30:
        return 0.7
    if age < 90:
        return 0.3
    return 0.0


def _ratio_factor(followers: float, following: float) -> float | None:
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (followers, following)):
        return None
    if following < 100:
        return 0.0
    return float(min(1.0, (following / (followers + 1.0)) / 10.0))


def behavior_score(factors: dict) -> float:
    """Skor 0-100 dengan renormalisasi bobot untuk faktor yang tersedia."""
    total = sum(FACTOR_WEIGHTS[k] for k, v in factors.items() if v is not None)
    if total <= 0:
        return 0.0
    s = sum(FACTOR_WEIGHTS[k] * v for k, v in factors.items() if v is not None) / total
    return round(100.0 * s, 1)


def build_accounts(posts: pd.DataFrame, narrative_col: pd.Series, narratives: pd.DataFrame) -> pd.DataFrame:
    """Hitung profil per akun."""
    cols = [
        "account_id", "posts", "first_seen", "last_seen", "platform", "mean_risk", "max_risk",
        "high_risk_posts", "narratives", "dup_share", "max_per_hour", "hour_entropy", "url_share",
        "followers", "following", "account_age_days", "behavior", "behavior_label", "evidence",
        "review_priority",
    ] + list(FACTOR_WEIGHTS)
    if len(posts) == 0:
        return pd.DataFrame(columns=cols)

    df = posts.copy()
    df["narrative"] = narrative_col.to_numpy()
    multi_acc_narr = set(narratives.loc[narratives["n_accounts"] > 1, "narrative"]) if len(narratives) else set()
    df["in_group_narr"] = df["narrative"].isin(multi_acc_narr)
    t0 = df["timestamp"].min()
    df["_sec"] = (df["timestamp"] - t0).dt.total_seconds()
    df["_hour"] = df["timestamp"].dt.hour
    df["_has_url"] = (df["n_urls"] > 0).astype(float)
    rows = []
    for acc, g in df.groupby("account_id", sort=False):
        n = len(g)
        max_ph = peak_window_count(g["_sec"].to_numpy(), 3600.0)
        entropy = _hour_entropy(g["_hour"].to_numpy()) if n >= 8 else None
        age = g["account_age_days"].median()
        followers = g["followers"].median()
        following = g["following"].median()
        factors = {
            "Laju unggah": min(1.0, max_ph / 10.0) if n >= 2 else 0.0,
            "Porsi konten kembar": float(g["in_group_narr"].mean()),
            "Aktivitas 24 jam": entropy,
            "Umur akun": _age_factor(age),
            "Rasio mengikuti": _ratio_factor(followers, following),
            "Tautan/spam": float(g["_has_url"].mean()),
        }
        score = behavior_score(factors)
        label = "Indikasi kuat tidak autentik" if score >= STRONG else ("Perlu dipantau" if score >= WATCH else "Normal")
        evidence = "Cukup" if n >= 5 else ("Terbatas" if n >= 2 else "Minim")
        mean_risk = float(g["risk"].mean())
        rows.append(
            {
                "account_id": acc,
                "posts": n,
                "first_seen": g["timestamp"].min(),
                "last_seen": g["timestamp"].max(),
                "platform": g["platform"].mode().iloc[0] if len(g["platform"].mode()) else "Tidak diketahui",
                "mean_risk": round(mean_risk, 1),
                "max_risk": round(float(g["risk"].max()), 1),
                "high_risk_posts": int((g["risk"] >= C.DEFAULT_HIGH_RISK).sum()),
                "narratives": int(g.loc[g["narrative"] != "", "narrative"].nunique()),
                "dup_share": round(factors["Porsi konten kembar"], 3),
                "max_per_hour": max_ph,
                "hour_entropy": None if entropy is None else round(entropy, 3),
                "url_share": round(factors["Tautan/spam"], 3),
                "followers": None if pd.isna(followers) else float(followers),
                "following": None if pd.isna(following) else float(following),
                "account_age_days": None if pd.isna(age) else float(age),
                "behavior": score,
                "behavior_label": label,
                "evidence": evidence,
                "review_priority": round(0.5 * score + 0.5 * mean_risk, 1),
                **{k: (None if v is None else round(float(v), 3)) for k, v in factors.items()},
            }
        )
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["review_priority", "posts"], ascending=False).reset_index(drop=True)
