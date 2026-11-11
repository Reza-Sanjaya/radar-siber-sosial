"""Peringatan dini: deret waktu, deteksi anomali (EWMA + z-score), dan
Indeks Siber Sosial (ISS) 0-100 beserta daftar peringatan.

Rumus ISS (jendela 24 jam terakhir sebelum waktu acuan):
    ISS = 100 x [ 0,30 x porsi konten berisiko tinggi (jenuh di 30%)
                + 0,20 x lonjakan anomali (z maks / 5)
                + 0,25 x narasi terkoordinasi aktif (jenuh di 3 narasi)
                + 0,15 x rata-rata prioritas 10 unggahan teratas / 100
                + 0,10 x konten berisiko yang menyasar institusi (jenuh di 5) ]
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C

ISS_WEIGHTS = {
    "Porsi konten berisiko tinggi": 0.30,
    "Lonjakan anomali volume/risiko": 0.20,
    "Narasi terkoordinasi aktif": 0.25,
    "Prioritas unggahan teratas": 0.15,
    "Konten berisiko menyasar institusi": 0.10,
}
Z_THRESHOLD = 2.5


def choose_freq(posts: pd.DataFrame) -> str:
    """Pilih granularitas deret waktu: per jam untuk rentang pendek, per hari untuk panjang."""
    if len(posts) == 0:
        return "h"
    span = posts["timestamp"].max() - posts["timestamp"].min()
    return "h" if span <= pd.Timedelta(days=10) else "D"


def time_series(posts: pd.DataFrame, freq: str, high_risk: float = C.DEFAULT_HIGH_RISK) -> pd.DataFrame:
    """Deret waktu volume & konten berisiko, dengan z-score anomali."""
    if len(posts) == 0:
        return pd.DataFrame(columns=["volume", "risky", "risky_share", "mean_risk", "z_volume", "z_risky",
                                     "anom_volume", "anom_risky"])
    d = posts[["timestamp", "risk"]].copy()
    d["risky"] = (d["risk"] >= high_risk).astype(int)
    d["bucket"] = d["timestamp"].dt.floor(freq)
    g = d.groupby("bucket").agg(volume=("risk", "size"), risky=("risky", "sum"), mean_risk=("risk", "mean"))
    full = pd.date_range(g.index.min(), g.index.max(), freq=freq)
    g = g.reindex(full)
    g["volume"] = g["volume"].fillna(0).astype(int)
    g["risky"] = g["risky"].fillna(0).astype(int)
    g["mean_risk"] = g["mean_risk"].fillna(0.0)
    g["risky_share"] = np.where(g["volume"] > 0, g["risky"] / g["volume"].where(g["volume"] > 0, 1), 0.0)
    span, win, minp = (24, 24, 6) if freq == "h" else (7, 7, 3)
    g["z_volume"] = _zscore(g["volume"].to_numpy(float), span, win, minp)
    g["z_risky"] = _zscore(g["risky"].to_numpy(float), span, win, minp)
    g["anom_volume"] = g["z_volume"] >= Z_THRESHOLD
    g["anom_risky"] = g["z_risky"] >= Z_THRESHOLD
    g.index.name = "bucket"
    return g


def _zscore(values: np.ndarray, span: int, window: int, min_periods: int) -> np.ndarray:
    """z-score pada akar-kuadrat hitungan terhadap baseline EWMA (geser 1 langkah)."""
    y = pd.Series(np.sqrt(np.clip(values, 0, None)))
    prev = y.shift(1)
    base = prev.ewm(span=span, min_periods=min_periods).mean()
    sd = prev.rolling(window, min_periods=min_periods).std()
    z = (y - base) / np.maximum(sd.fillna(0.0), 0.5)
    return np.round(z.fillna(0.0).to_numpy(float), 2)


def episodes(series: pd.DataFrame, flag_col: str, z_col: str, value_col: str) -> pd.DataFrame:
    """Gabungkan bucket anomali berurutan menjadi episode."""
    cols = ["start", "end", "peak_z", "total", "buckets"]
    if len(series) == 0 or not series[flag_col].any():
        return pd.DataFrame(columns=cols)
    out, start, prev_idx, peak, total, k = [], None, None, 0.0, 0, 0
    idx = list(series.index)
    for i, (ts, row) in enumerate(series.iterrows()):
        if row[flag_col]:
            if start is None:
                start, peak, total, k = ts, 0.0, 0, 0
            peak = max(peak, float(row[z_col]))
            total += int(row[value_col])
            k += 1
            prev_idx = i
        elif start is not None:
            out.append({"start": start, "end": idx[prev_idx], "peak_z": round(peak, 2), "total": total, "buckets": k})
            start = None
    if start is not None:
        out.append({"start": start, "end": idx[prev_idx], "peak_z": round(peak, 2), "total": total, "buckets": k})
    return pd.DataFrame(out, columns=cols)


def compute_iss(
    posts: pd.DataFrame,
    narratives: pd.DataFrame,
    series: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
    window_hours: int = 24,
    high_risk: float = C.DEFAULT_HIGH_RISK,
) -> dict:
    """Hitung ISS untuk jendela (as_of - window_hours, as_of]."""
    empty = {
        "iss": 0.0, "status": "AMAN", "components": [], "n_posts": 0, "as_of": as_of,
        "window_start": None, "high_share": 0.0, "active_narratives": 0, "tni_risky": 0,
    }
    if len(posts) == 0:
        return empty
    end = pd.Timestamp(as_of) if as_of is not None else posts["timestamp"].max()
    start = end - pd.Timedelta(hours=window_hours)
    win = posts[(posts["timestamp"] > start) & (posts["timestamp"] <= end)]
    empty.update({"as_of": end, "window_start": start})
    if len(win) == 0:
        return empty

    high_share = float((win["risk"] >= high_risk).mean())
    c1 = min(1.0, high_share / 0.30)

    c2 = 0.0
    if len(series):
        sw = series[(series.index > start.floor("h") - pd.Timedelta(hours=1)) & (series.index <= end)]
        if len(sw):
            zmax = float(max(sw["z_volume"].max(), sw["z_risky"].max()))
            c2 = float(min(1.0, max(0.0, zmax) / 5.0))

    active = 0
    if len(narratives):
        m = (
            (narratives["coordination"] >= C.COORD_INDICATION)
            & (narratives["mean_risk"] >= 25)
            & (narratives["n_accounts"] > 1)
            & (narratives["last_seen"] > start)
            & (narratives["first_seen"] <= end)
        )
        active = int(m.sum())
    c3 = min(1.0, active / 3.0)

    top = win.nlargest(10, "priority")["priority"]
    c4 = float(top.mean() / 100.0) if len(top) else 0.0

    tni_risky = int(((win["risk"] >= high_risk) & win["tni_target"]).sum())
    c5 = min(1.0, tni_risky / 5.0)

    values = [c1, c2, c3, c4, c5]
    details = [
        f"{high_share * 100:.0f}% unggahan berisiko tinggi",
        f"z maks {c2 * 5:.1f}",
        f"{active} narasi terkoordinasi aktif",
        f"rata-rata prioritas top-10 = {c4 * 100:.0f}",
        f"{tni_risky} unggahan berisiko menyasar institusi",
    ]
    comps = []
    iss = 0.0
    for (name, w), v, det in zip(ISS_WEIGHTS.items(), values, details):
        comps.append({"komponen": name, "bobot": w, "nilai": round(v, 3), "kontribusi": round(100 * w * v, 1), "detail": det})
        iss += 100 * w * v
    iss = round(float(iss), 1)
    return {
        "iss": iss, "status": C.status_level(iss), "components": comps, "n_posts": len(win), "as_of": end,
        "window_start": start, "high_share": high_share, "active_narratives": active, "tni_risky": tni_risky,
    }


def iss_trend(
    posts: pd.DataFrame,
    narratives: pd.DataFrame,
    series: pd.DataFrame,
    step_hours: int = 6,
    window_hours: int = 24,
    high_risk: float = C.DEFAULT_HIGH_RISK,
) -> pd.DataFrame:
    """ISS pada titik-titik waktu berkala (untuk grafik tren & fitur replay)."""
    if len(posts) == 0:
        return pd.DataFrame(columns=["as_of", "iss", "status"])
    end_max = posts["timestamp"].max()
    first = posts["timestamp"].min().ceil(f"{step_hours}h")
    ends = list(pd.date_range(first, end_max, freq=f"{step_hours}h"))
    if not ends or ends[-1] < end_max:
        ends.append(end_max)
    rows = []
    for e in ends:
        r = compute_iss(posts, narratives, series, as_of=e, window_hours=window_hours, high_risk=high_risk)
        rows.append({"as_of": e, "iss": r["iss"], "status": r["status"]})
    return pd.DataFrame(rows)


def build_alerts(
    posts: pd.DataFrame,
    narratives: pd.DataFrame,
    accounts: pd.DataFrame,
    series: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
    window_hours: int = 24,
    high_risk: float = C.DEFAULT_HIGH_RISK,
) -> list[dict]:
    """Daftar peringatan berbasis aturan (setiap peringatan menjelaskan pemicunya)."""
    alerts: list[dict] = []
    if len(posts) == 0:
        return alerts
    end = pd.Timestamp(as_of) if as_of is not None else posts["timestamp"].max()
    start = end - pd.Timedelta(hours=window_hours)
    win = posts[(posts["timestamp"] > start) & (posts["timestamp"] <= end)]
    if len(win) == 0:
        return alerts

    def add(level: str, kind: str, title: str, detail: str) -> None:
        alerts.append({"level": level, "kind": kind, "title": title, "detail": detail})

    # lonjakan
    if len(series):
        sw = series[(series.index > start - pd.Timedelta(hours=1)) & (series.index <= end)]
        for col, z, label in (("anom_volume", "z_volume", "volume unggahan"), ("anom_risky", "z_risky", "konten berisiko")):
            if len(sw) and sw[col].any():
                peak = sw.loc[sw[col], z].max()
                when = sw[z].idxmax()
                add("SIAGA" if peak >= 4 else "WASPADA", "lonjakan",
                    f"Lonjakan {label}",
                    f"z-score puncak {peak:.1f} pada {when:%d %b %Y %H:%M} (ambang {Z_THRESHOLD}).")

    # narasi terkoordinasi
    if len(narratives):
        active = narratives[
            (narratives["last_seen"] > start) & (narratives["first_seen"] <= end) & (narratives["mean_risk"] >= 25)
        ]
        for _, n in active.iterrows():
            if n["n_accounts"] > 1 and n["coordination"] >= C.COORD_STRONG:
                add("AWAS" if n["mean_risk"] >= 50 else "SIAGA", "koordinasi",
                    f"Narasi {n['narrative']} terkoordinasi kuat ({n['top_label']})",
                    f"{n['size']} unggahan dari {n['n_accounts']} akun, skor koordinasi {n['coordination']:.0f}, "
                    f"rata-rata risiko {n['mean_risk']:.0f}.")
            elif n["n_accounts"] > 1 and n["coordination"] >= C.COORD_INDICATION:
                add("WASPADA", "koordinasi",
                    f"Narasi {n['narrative']} menunjukkan indikasi koordinasi ({n['top_label']})",
                    f"{n['size']} unggahan dari {n['n_accounts']} akun, skor koordinasi {n['coordination']:.0f}.")
            if n["tni_share"] >= 0.5 and n["mean_risk"] >= 40:
                add("SIAGA", "institusi", f"Narasi {n['narrative']} menyasar institusi/satuan",
                    f"{n['tni_share'] * 100:.0f}% unggahan menyebut institusi dengan rata-rata risiko {n['mean_risk']:.0f}.")

    # kategori spesifik
    risky = win[win["risk"] >= high_risk]
    n_scam = int((risky["label"] == C.CAT_PENIPUAN).sum())
    if n_scam >= 5:
        add("SIAGA", "penipuan", "Gelombang penipuan/phishing", f"{n_scam} unggahan berisiko tinggi bermuatan penipuan.")
    elif n_scam >= 1:
        add("WASPADA", "penipuan", "Indikasi penipuan/phishing", f"{n_scam} unggahan berisiko tinggi bermuatan penipuan.")
    n_dox = int(((risky["label"] == C.CAT_DOXXING) | (risky["pii_nik"] > 0)).sum())
    if n_dox >= 1:
        add("SIAGA", "doxxing", "Dugaan pembocoran data pribadi",
            f"{n_dox} unggahan memuat indikasi data pribadi/ajakan mencari target (data ditampilkan tersamarkan).")
    n_viol = int(((win["label"] == C.CAT_KEKERASAN) & (win["risk"] >= 60)).sum())
    if n_viol >= 1:
        add("AWAS", "kekerasan", "Ajakan kekerasan/kebencian", f"{n_viol} unggahan dengan skor risiko >= 60 pada kategori kekerasan.")

    # akun tidak autentik aktif pada jendela
    if len(accounts):
        active_acc = set(win["account_id"].unique())
        strong = accounts[(accounts["behavior_label"] == "Indikasi kuat tidak autentik") & accounts["account_id"].isin(active_acc)]
        if len(strong) >= 5:
            add("SIAGA", "akun", "Jaringan akun tidak autentik aktif", f"{len(strong)} akun dengan indikasi kuat tidak autentik aktif pada jendela analisis.")
        elif len(strong) >= 1:
            add("WASPADA", "akun", "Akun dengan indikasi tidak autentik", f"{len(strong)} akun perlu verifikasi manual.")

    order = {"AWAS": 0, "SIAGA": 1, "WASPADA": 2}
    alerts.sort(key=lambda a: order.get(a["level"], 3))
    return alerts
