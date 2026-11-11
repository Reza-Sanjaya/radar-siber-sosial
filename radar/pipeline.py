"""Orkestrasi seluruh analisis: data terstandar -> hasil lengkap (dict)."""
from __future__ import annotations

import pandas as pd

from . import constants as C
from .accounts import build_accounts
from .analyzer import analyze_df
from .coordination import build_narratives, cluster_posts, merge_related_clusters
from .text_utils import extract_hashtags
from .early_warning import (
    build_alerts,
    choose_freq,
    compute_iss,
    episodes,
    iss_trend,
    time_series,
)


def run_pipeline(
    df: pd.DataFrame,
    sim_threshold: float = C.DEFAULT_SIM_THRESHOLD,
    min_cluster: int = C.DEFAULT_MIN_CLUSTER,
    high_risk: float = C.DEFAULT_HIGH_RISK,
) -> dict:
    """Jalankan analisis penuh. `df` harus hasil `radar.data.standardize`."""
    posts = analyze_df(df)
    tokens_list = posts["tokens"].tolist()
    labels = cluster_posts(tokens_list, sim_threshold, min_cluster)
    seconds = (posts["timestamp"] - posts["timestamp"].min()).dt.total_seconds().to_numpy()
    labels = merge_related_clusters(
        labels, tokens_list, seconds, [extract_hashtags(t) for t in posts["text"].tolist()], posts["risk"].to_numpy()
    )
    narratives, narr_col = build_narratives(posts, labels)
    posts["narrative"] = narr_col.to_numpy()
    accounts = build_accounts(posts, narr_col, narratives)

    freq = choose_freq(posts)
    series = time_series(posts, freq, high_risk)
    ep_vol = episodes(series, "anom_volume", "z_volume", "volume")
    ep_risk = episodes(series, "anom_risky", "z_risky", "risky")
    iss = compute_iss(posts, narratives, series, high_risk=high_risk)
    trend = iss_trend(posts, narratives, series, high_risk=high_risk)
    alerts = build_alerts(posts, narratives, accounts, series, high_risk=high_risk)

    posts = posts.drop(columns=["tokens", "norm"])
    meta = {
        "n_posts": int(len(posts)),
        "n_accounts": int(posts["account_id"].nunique()) if len(posts) else 0,
        "start": posts["timestamp"].min() if len(posts) else None,
        "end": posts["timestamp"].max() if len(posts) else None,
        "freq": freq,
        "n_narratives": int(len(narratives)),
        "n_high_risk": int((posts["risk"] >= high_risk).sum()) if len(posts) else 0,
        "high_risk": float(high_risk),
        "sim_threshold": float(sim_threshold),
        "min_cluster": int(min_cluster),
    }
    return {
        "posts": posts,
        "narratives": narratives,
        "accounts": accounts,
        "series": series,
        "episodes_volume": ep_vol,
        "episodes_risky": ep_risk,
        "iss": iss,
        "trend": trend,
        "alerts": alerts,
        "meta": meta,
    }
