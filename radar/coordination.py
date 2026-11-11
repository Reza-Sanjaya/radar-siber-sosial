"""Pengelompokan narasi (near-duplicate / parafrase) & skor koordinasi.

Metode:
  1. Setiap unggahan diubah menjadi himpunan token konten.
  2. Himpunan identik digabung langsung (copy-paste murni).
  3. Kandidat pasangan dicari lewat indeks terbalik (hanya token yang tidak terlalu umum),
     lalu kemiripan Jaccard dihitung; pasangan >= ambang digabung (union-find).
  4. Kelompok >= ukuran minimal menjadi "narasi".
  5. Setiap narasi diberi Skor Koordinasi 0-100 dari lima sinyal yang transparan.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from . import constants as C
from .text_utils import extract_hashtags, jaccard

_CAND_BUDGET = 1500        # batas posting yang dipindai per dokumen
_MAX_SMALL_DF_CAP = 300


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def cluster_posts(
    tokens_list: list[list[str]],
    sim_threshold: float = C.DEFAULT_SIM_THRESHOLD,
    min_size: int = C.DEFAULT_MIN_CLUSTER,
) -> np.ndarray:
    """Kembalikan label klaster per unggahan (-1 = bukan bagian narasi)."""
    n = len(tokens_list)
    labels = np.full(n, -1, dtype=int)
    if n == 0:
        return labels
    sim_threshold = float(min(max(sim_threshold, 0.2), 0.95))
    min_size = max(2, int(min_size))

    # 1) himpunan unik
    uniq: dict[frozenset, list[int]] = {}
    for i, toks in enumerate(tokens_list):
        if not toks:
            continue
        uniq.setdefault(frozenset(toks), []).append(i)
    keys = list(uniq.keys())
    m = len(keys)
    if m == 0:
        return labels
    uf = _UnionFind(m)

    # 2) indeks terbalik untuk himpunan cukup panjang
    long_ids = [u for u, k in enumerate(keys) if len(k) >= C.MIN_TOKENS_FOR_CLUSTER]
    postings: dict[str, list[int]] = defaultdict(list)
    for u in long_ids:
        for tok in keys[u]:
            postings[tok].append(u)
    df_cap = int(min(max(60, 0.05 * len(long_ids)), _MAX_SMALL_DF_CAP))
    usable = {t: lst for t, lst in postings.items() if len(lst) <= df_cap}

    for u in long_ids:
        toks = sorted((t for t in keys[u] if t in usable), key=lambda t: len(usable[t]))
        counter: Counter = Counter()
        budget = _CAND_BUDGET
        for t in toks:
            lst = usable[t]
            if len(lst) > budget:
                break
            budget -= len(lst)
            counter.update(v for v in lst if v > u)
        need = 2 if len(keys[u]) >= 4 else 1
        for v, shared in counter.items():
            if shared < need:
                continue
            if jaccard(keys[u], keys[v]) >= sim_threshold:
                uf.union(u, v)

    # 3) hitung ukuran klaster dalam jumlah unggahan
    root_members: dict[int, list[int]] = defaultdict(list)
    for u, k in enumerate(keys):
        root_members[uf.find(u)].extend(uniq[k])
    cid = 0
    for root, members in sorted(root_members.items(), key=lambda kv: -len(kv[1])):
        if len(members) >= min_size:
            labels[members] = cid
            cid += 1
    return labels


def peak_window_count(seconds: np.ndarray, window_s: float = 3600.0) -> int:
    """Jumlah unggahan terbanyak dalam satu jendela waktu geser."""
    if len(seconds) == 0:
        return 0
    s = np.sort(seconds)
    j = 0
    best = 0
    for i in range(len(s)):
        while s[i] - s[j] > window_s:
            j += 1
        best = max(best, i - j + 1)
    return best


def _medoid(token_sets: list[frozenset], cap: int = 150) -> int:
    """Indeks anggota yang paling mewakili (rata-rata Jaccard tertinggi)."""
    k = min(len(token_sets), cap)
    if k <= 1:
        return 0
    best_i, best_score = 0, -1.0
    for i in range(k):
        score = sum(jaccard(token_sets[i], token_sets[j]) for j in range(k) if j != i) / (k - 1)
        if score > best_score:
            best_i, best_score = i, score
    return best_i


def coordination_components(
    n_posts: int,
    n_accounts: int,
    peak_in_window: int,
    tightness: float,
    new_share: float | None,
    overlap_share: float,
) -> tuple[float, dict]:
    """Skor koordinasi 0-100 + rincian komponen (semua 0-1).

    Skor = 100 x kepadatan-waktu x (0,5 + 0,5 x pendukung) x keyakinan-ukuran
      kepadatan-waktu : porsi unggahan dalam jendela 60 menit terpadat
      pendukung       : 0,40 keragaman akun + 0,30 kemiripan teks + 0,20 akun baru + 0,10 akun lintas-narasi
      keyakinan-ukuran: min(1, akar(ukuran / 8)) agar klaster kecil tidak dinilai berlebihan
    Keragaman akun TIDAK berdiri sendiri: ribuan akun yang menulis hal serupa pada waktu
    berbeda (tren organik) tidak dianggap terkoordinasi.
    """
    burst = (peak_in_window / n_posts) if n_posts else 0.0
    comp = {
        "Kepadatan waktu": float(burst),
        "Keragaman akun": min(1.0, max(0, n_accounts - 1) / 9.0),
        "Kemiripan teks": float(tightness),
        "Akun baru": None if new_share is None or (isinstance(new_share, float) and math.isnan(new_share)) else float(new_share),
        "Akun lintas-narasi": float(overlap_share),
    }
    weights = {"Keragaman akun": 0.40, "Kemiripan teks": 0.30, "Akun baru": 0.20, "Akun lintas-narasi": 0.10}
    total_w = sum(w for k, w in weights.items() if comp[k] is not None)
    support = sum(weights[k] * comp[k] for k in weights if comp[k] is not None) / total_w if total_w else 0.0
    confidence = min(1.0, math.sqrt(n_posts / 8.0)) if n_posts else 0.0
    score = 100.0 * burst * (0.5 + 0.5 * support) * confidence
    return round(min(100.0, score), 1), comp


def coordination_label(score: float, n_accounts: int, size: int = 0, tightness: float = 0.0) -> str:
    if n_accounts <= 1:
        return "Spam akun tunggal"
    if score >= C.COORD_STRONG:
        return "Terkoordinasi kuat"
    if score >= C.COORD_INDICATION:
        return "Indikasi koordinasi"
    if size / n_accounts >= 1.6 and tightness >= 0.7:
        return "Spam berulang (sedikit akun)"
    return "Tidak terindikasi koordinasi"


def merge_related_clusters(
    labels: np.ndarray,
    tokens_list: list[list[str]],
    seconds: np.ndarray,
    hashtags_list: list[list[str]],
    risk: np.ndarray,
    min_risk: float = 25.0,
    max_gap_hours: float = 24.0,
    core_sim: float = 0.30,
    tag_share: float = 0.30,
) -> np.ndarray:
    """Gabungkan narasi berisiko yang tampaknya satu kampanye (variasi kalimat berbeda).

    Dua klaster digabung bila berdekatan waktu (<= 24 jam) DAN (inti token mirip >= 0,30
    ATAU berbagi tagar khas yang dipakai >= 30% unggahan di kedua klaster).
    Hanya klaster berisiko (rata-rata risiko >= 25) yang dipertimbangkan agar
    frasa umum yang kebetulan sama tidak ikut tergabung.
    """
    out = labels.copy()
    ids = sorted(c for c in set(labels.tolist()) if c >= 0)
    if len(ids) < 2:
        return out
    n_total = len(labels)
    tag_df: Counter = Counter()
    for tags in hashtags_list:
        tag_df.update(set(tags))
    tag_cap = max(30, int(0.10 * n_total))

    info = {}
    for c in ids:
        idx = np.where(labels == c)[0]
        if float(np.mean(risk[idx])) < min_risk:
            continue
        counts: Counter = Counter()
        tag_counts: Counter = Counter()
        for i in idx:
            counts.update(set(tokens_list[i]))
            tag_counts.update(set(hashtags_list[i]))
        core = {t for t, k in counts.items() if k >= 0.5 * len(idx)}
        tags = {t for t, k in tag_counts.items() if k >= tag_share * len(idx) and tag_df[t] <= tag_cap}
        info[c] = (core, tags, float(seconds[idx].min()), float(seconds[idx].max()))
    keys = sorted(info)
    uf = _UnionFind(len(keys))
    for a in range(len(keys)):
        ca, ta, sa, ea = info[keys[a]]
        for b in range(a + 1, len(keys)):
            cb, tb, sb, eb = info[keys[b]]
            gap = max(0.0, max(sa, sb) - min(ea, eb)) / 3600.0
            if gap > max_gap_hours:
                continue
            if (ca and cb and jaccard(ca, cb) >= core_sim) or (ta & tb):
                uf.union(a, b)
    root_label = {}
    for i, c in enumerate(keys):
        root_label[c] = keys[uf.find(i)]
    for c, new in root_label.items():
        if c != new:
            out[labels == c] = new
    return out


def build_narratives(posts: pd.DataFrame, labels: np.ndarray) -> tuple[pd.DataFrame, pd.Series]:
    """Susun tabel narasi dari unggahan terskor + label klaster.

    Mengembalikan (tabel narasi, Series id narasi per unggahan; "" bila tidak ada).
    """
    empty_cols = [
        "narrative", "size", "n_accounts", "first_seen", "last_seen", "span_hours", "peak_hour_posts",
        "posts_per_hour", "mean_risk", "max_risk", "top_label", "tightness", "new_account_share",
        "overlap_share", "coordination", "coord_label", "tni_share", "interactions", "hashtags",
        "origin_account", "origin_time", "sample_text", "priority", "_cluster",
    ]
    narr_col = pd.Series([""] * len(posts), index=posts.index, dtype="object")
    valid = sorted(c for c in set(labels.tolist()) if c >= 0)
    if not valid:
        return pd.DataFrame(columns=empty_cols), narr_col

    # akun yang muncul pada >= 2 narasi
    acc_clusters: dict[str, set[int]] = defaultdict(set)
    for acc, cl in zip(posts["account_id"].to_numpy(), labels):
        if cl >= 0:
            acc_clusters[acc].add(int(cl))
    multi_accounts = {a for a, cs in acc_clusters.items() if len(cs) >= 2}

    rows = []
    t0 = posts["timestamp"].min()
    for cl in valid:
        idx = np.where(labels == cl)[0]
        sub = posts.iloc[idx].sort_values("timestamp", kind="stable")
        seconds = (sub["timestamp"] - t0).dt.total_seconds().to_numpy()
        size = len(sub)
        accounts = sub["account_id"].unique()
        n_acc = len(accounts)
        peak = peak_window_count(seconds, 3600.0)
        span_h = max((seconds.max() - seconds.min()) / 3600.0, 0.0) if size else 0.0

        sets = [frozenset(t) for t in sub["tokens"].tolist()]
        mi = _medoid(sets)
        med = sets[mi]
        cap = min(len(sets), 300)
        tightness = float(np.mean([jaccard(s, med) for s in sets[:cap]])) if cap else 0.0

        ages = sub["account_age_days"].dropna()
        new_share = float((ages < 30).mean()) if len(ages) >= max(3, 0.3 * size) else None
        overlap = sum(1 for a in accounts if a in multi_accounts) / n_acc if n_acc else 0.0

        coord, _comp = coordination_components(size, n_acc, peak, tightness, new_share, overlap)

        tags: Counter = Counter()
        for t in sub["text"].tolist()[:500]:
            tags.update(extract_hashtags(t))
        top_tags = ", ".join(f"#{h}" for h, _ in tags.most_common(3))

        label_counts = sub["label"].value_counts()
        risky = [lab for lab in label_counts.index if lab in C.RISK_CATEGORIES]
        top_label = risky[0] if risky else str(label_counts.index[0])
        mean_risk = float(sub["risk"].mean())
        tni_share = float(sub["tni_relevant"].mean())
        scale = min(1.0, math.log1p(size) / math.log1p(60))
        priority = mean_risk * (0.55 + 0.25 * coord / 100.0 + 0.20 * scale)
        if tni_share >= 0.5:
            priority *= 1.1
        priority = round(min(100.0, priority), 1)

        rows.append(
            {
                "size": size,
                "n_accounts": n_acc,
                "first_seen": sub["timestamp"].iloc[0],
                "last_seen": sub["timestamp"].iloc[-1],
                "span_hours": round(span_h, 2),
                "peak_hour_posts": peak,
                "posts_per_hour": round(size / max(span_h, 1.0), 2),
                "mean_risk": round(mean_risk, 1),
                "max_risk": round(float(sub["risk"].max()), 1),
                "top_label": top_label,
                "tightness": round(tightness, 3),
                "new_account_share": None if new_share is None else round(new_share, 3),
                "overlap_share": round(overlap, 3),
                "coordination": coord,
                "coord_label": coordination_label(coord, n_acc, size, tightness),
                "tni_share": round(tni_share, 3),
                "interactions": int(sub[["likes", "shares", "replies"]].sum().sum()),
                "hashtags": top_tags,
                "origin_account": sub["account_id"].iloc[0],
                "origin_time": sub["timestamp"].iloc[0],
                "sample_text": sub["text_display"].iloc[min(mi, len(sub) - 1)],
                "priority": priority,
                "_cluster": cl,
            }
        )

    narr = pd.DataFrame(rows).sort_values(["priority", "size"], ascending=False).reset_index(drop=True)
    narr.insert(0, "narrative", [f"N-{i + 1:02d}" for i in range(len(narr))])
    cl_to_id = dict(zip(narr["_cluster"], narr["narrative"]))
    narr_col = pd.Series(
        [cl_to_id.get(int(c), "") if c >= 0 else "" for c in labels], index=posts.index, dtype="object"
    )
    return narr, narr_col
