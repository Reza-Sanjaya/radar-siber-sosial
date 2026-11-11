"""Analisis konten: skor risiko yang dapat dijelaskan (explainable).

Alur per teks:
    1. normalisasi (slang, huruf berulang, leet)
    2. cocokkan kamus isyarat per kategori (+ penanganan negasi)
    3. aturan ko-okurensi (identitas+permusuhan, ajakan+kekerasan, rekrutmen+bayar, dll)
    4. isyarat klarifikasi / kredibilitas menahan false positive
    5. gabungkan kategori dengan noisy-OR -> skor risiko 0-100

Seluruh isyarat yang aktif dikembalikan sehingga setiap skor bisa diaudit.
"""
from __future__ import annotations

import html
import math
import re
from typing import Iterable

import numpy as np
import pandas as pd

from . import constants as C
from . import lexicon as L
from .text_utils import (
    content_tokens,
    find_pii,
    mask_pii,
    normalize,
    safe_text,
    surface_features,
)

_SATURATION = 2.2  # raw / 2.2 -> eksponensial (raw 2 ~ 0.60, raw 4 ~ 0.84)
NEGATION_FACTOR = 0.15
DEBUNK_FACTOR = 0.35


def _any_regex(entries) -> re.Pattern:
    return re.compile("|".join(f"(?:{p.pattern})" for p, _, _ in entries))


# Prefilter gabungan agar teks netral cepat dilewati
_PREFILTER = {cat: _any_regex(entries) for cat, entries in L.CATEGORY_LEXICONS.items()}
_PREFILTER_ID = _any_regex(L.IDENTITY)
_PREFILTER_INST = _any_regex(L.INSTITUSI)
_PREFILTER_CTA = _any_regex(L.CTA)
_PREFILTER_DEBUNK = _any_regex(L.DEBUNK)
_PREFILTER_CRED = _any_regex(L.CREDIBILITY)


def _is_negated(norm: str, start: int) -> bool:
    """True bila ada kata negasi dalam 3 kata sebelum posisi `start` (satu klausa)."""
    prefix = norm[:start]
    clause = re.split(r"[.!?;:\n]", prefix)[-1]
    words = re.findall(r"\w+", clause)[-3:]
    return any(w in L.NEGATORS for w in words)


def _scan(norm: str, entries, negation: bool) -> list[dict]:
    hits = []
    for pat, weight, label in entries:
        m = pat.search(norm)
        if not m:
            continue
        negated = _is_negated(norm, m.start()) if negation else False
        hits.append(
            {
                "cue": label,
                "weight": weight * (NEGATION_FACTOR if negated else 1.0),
                "base_weight": weight,
                "negated": negated,
                "span": (m.start(), m.end()),
            }
        )
    return hits


def _saturate(raw: float) -> float:
    return 1.0 - math.exp(-max(raw, 0.0) / _SATURATION)


def analyze_text(value) -> dict:
    """Analisis satu teks. Aman untuk input kosong / bukan string."""
    raw_text = safe_text(value)
    norm = normalize(raw_text, C.MAX_TEXT_CHARS)
    feats = surface_features(raw_text)
    pii = find_pii(raw_text)

    raw = {cat: 0.0 for cat in C.RISK_CATEGORIES}
    cues: list[dict] = []
    hits_by_cat: dict[str, list[dict]] = {cat: [] for cat in C.RISK_CATEGORIES}

    # 1) isyarat per kategori
    if norm:
        for cat, entries in L.CATEGORY_LEXICONS.items():
            if not _PREFILTER[cat].search(norm):
                continue
            hits = _scan(norm, entries, negation=cat in L.NEGATION_SENSITIVE)
            hits_by_cat[cat] = hits
            raw[cat] += sum(h["weight"] for h in hits)
            for h in hits:
                cues.append({"category": cat, **h})

    has_identity = bool(norm and _PREFILTER_ID.search(norm))
    has_institution = bool(norm and _PREFILTER_INST.search(norm))
    has_cta = bool(norm and _PREFILTER_CTA.search(norm))

    def add_rule(cat: str, label: str, weight: float) -> None:
        raw[cat] += weight
        cues.append(
            {"category": cat, "cue": label, "weight": weight, "base_weight": weight,
             "negated": False, "span": None}
        )

    # 2) aturan ko-okurensi
    live_hostile = [
        h for h in hits_by_cat[C.CAT_PROVOKASI] + hits_by_cat[C.CAT_KEKERASAN] if not h["negated"]
    ]
    if has_identity and live_hostile:
        add_rule(C.CAT_PROVOKASI, "aturan: penanda identitas + diksi permusuhan", 2.0)
    live_violence = [h for h in hits_by_cat[C.CAT_KEKERASAN] if not h["negated"] and h["base_weight"] >= 1.0]
    if has_cta and live_violence:
        add_rule(C.CAT_KEKERASAN, "aturan: ajakan bertindak + diksi kekerasan", 1.0)
    if has_institution and norm and L.RECRUIT_RE.search(norm) and L.PAYMENT_RE.search(norm):
        add_rule(C.CAT_PENIPUAN, "aturan: rekrutmen institusi + permintaan pembayaran", 2.0)
    if pii["nik"]:
        add_rule(C.CAT_DOXXING, "pola: NIK 16 digit dalam teks", 1.5)
    if pii["phone"]:
        add_rule(C.CAT_DOXXING, "pola: nomor telepon dalam teks", 0.5)
        if norm and L.DOXX_CONTEXT_RE.search(norm):
            add_rule(C.CAT_DOXXING, "aturan: nomor telepon + konteks pembocoran", 1.0)
    if feats["n_shorteners"]:
        add_rule(C.CAT_PENIPUAN, "pola: tautan pemendek (shortener)", min(1.2, 0.6 * feats["n_shorteners"]))

    # 3) gaya sensasional memperkuat disinformasi hanya bila sudah ada isyarat
    if raw[C.CAT_DISINFO] > 0:
        if feats["caps_ratio"] > 0.5:
            add_rule(C.CAT_DISINFO, "gaya: dominan huruf kapital", 0.6)
        if feats["exclaims"] >= 3:
            add_rule(C.CAT_DISINFO, "gaya: tanda seru berlebihan", 0.5)

    # 4) isyarat kredibilitas & klarifikasi
    credibility = 0.0
    if norm and raw[C.CAT_DISINFO] > 0 and _PREFILTER_CRED.search(norm):
        cred_hits = _scan(norm, L.CREDIBILITY, negation=False)
        credibility = min(1.5, -sum(h["weight"] for h in cred_hits))
        raw[C.CAT_DISINFO] = max(0.0, raw[C.CAT_DISINFO] - credibility)
        for h in cred_hits:
            cues.append({"category": "Kredibilitas", **h})

    debunk_raw = 0.0
    is_debunk = False
    if norm and _PREFILTER_DEBUNK.search(norm):
        debunk_norm = L.DEBUNK_NEGATE_RE.sub(" ", norm)
        d_hits = _scan(debunk_norm, L.DEBUNK, negation=False)
        debunk_raw = sum(h["weight"] for h in d_hits)
        is_debunk = debunk_raw >= 1.0
        if is_debunk:
            for cat in raw:
                raw[cat] *= DEBUNK_FACTOR
            for h in d_hits:
                h = dict(h)
                h["span"] = None  # posisi di teks yang sudah dimodifikasi tidak dipakai
                cues.append({"category": C.CAT_KLARIFIKASI, **h})

    # 5) skor kategori & gabungan
    cat_scores = {cat: _saturate(raw[cat]) for cat in C.RISK_CATEGORIES}
    survive = 1.0
    for cat, s in cat_scores.items():
        survive *= 1.0 - C.CATEGORY_WEIGHT[cat] * s
    risk = round(100.0 * (1.0 - survive), 1)

    weighted = {cat: C.CATEGORY_WEIGHT[cat] * cat_scores[cat] for cat in cat_scores}
    top_cat = max(weighted, key=weighted.get) if weighted else C.CAT_NETRAL
    if is_debunk and risk < C.BINARY_RISK_THRESHOLD:
        label = C.CAT_KLARIFIKASI
    elif risk < 20.0:
        label = C.CAT_NETRAL
    else:
        label = top_cat

    tni_relevant = has_institution
    tni_target = bool(tni_relevant and risk >= 25.0)

    explanation = _explain(label, risk, cues, tni_target, is_debunk, credibility)
    return {
        "norm": norm,
        "risk": risk,
        "level": C.risk_level(risk),
        "label": label,
        "cat_scores": {cat: round(100.0 * s, 1) for cat, s in cat_scores.items()},
        "cues": cues,
        "tni_relevant": tni_relevant,
        "tni_target": tni_target,
        "is_debunk": is_debunk,
        "pii": pii,
        "feats": feats,
        "explanation": explanation,
    }


def _explain(label: str, risk: float, cues: list[dict], tni_target: bool,
             is_debunk: bool, credibility: float) -> str:
    active = [c for c in cues if c["category"] in C.RISK_CATEGORIES and not c["negated"]]
    if not active:
        if is_debunk:
            return "Konten bersifat klarifikasi/cek fakta; tidak ada isyarat risiko yang dominan."
        return "Tidak ditemukan isyarat risiko yang bermakna pada teks ini."
    by_cat: dict[str, list[str]] = {}
    for c in sorted(active, key=lambda x: -x["weight"]):
        by_cat.setdefault(c["category"], []).append(c["cue"])
    parts = []
    for cat, items in by_cat.items():
        shown = ", ".join(f"“{i}”" for i in items[:4])
        more = f" (+{len(items) - 4} lainnya)" if len(items) > 4 else ""
        parts.append(f"{cat}: {shown}{more}")
    if risk < 20.0:
        text = "Isyarat lemah terdeteksi (" + "; ".join(parts) + "), belum cukup menaikkan risiko."
    else:
        text = "Isyarat aktif → " + "; ".join(parts) + "."
    if is_debunk:
        text += " Ada konteks klarifikasi yang menurunkan skor."
    if credibility > 0:
        text += " Ada rujukan sumber resmi yang menurunkan skor disinformasi."
    if tni_target:
        text += " Konten menyebut institusi/satuan sehingga prioritas dinaikkan."
    return text


def reach_score(likes, shares, replies) -> np.ndarray:
    """Skor jangkauan 0-100 (skala log; 2000 interaksi berbobot ~ 100)."""
    likes = np.nan_to_num(np.asarray(likes, dtype=float), nan=0.0)
    shares = np.nan_to_num(np.asarray(shares, dtype=float), nan=0.0)
    replies = np.nan_to_num(np.asarray(replies, dtype=float), nan=0.0)
    eng = np.clip(likes, 0, None) + 2.0 * np.clip(shares, 0, None) + 1.5 * np.clip(replies, 0, None)
    return np.round(100.0 * np.minimum(1.0, np.log1p(eng) / math.log1p(2000.0)), 1)


def priority_score(risk, reach, tni_target) -> np.ndarray:
    """Prioritas tindak = risiko x (0,6 + 0,4 x jangkauan) x 1,15 bila menyasar institusi."""
    risk = np.asarray(risk, dtype=float)
    reach = np.asarray(reach, dtype=float)
    boost = np.where(np.asarray(tni_target, dtype=bool), 1.15, 1.0)
    return np.round(np.minimum(100.0, risk * (0.6 + 0.4 * reach / 100.0) * boost), 1)


def analyze_df(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan kolom analisis ke DataFrame yang memuat kolom `text`."""
    out = df.copy()
    cache: dict[str, dict] = {}
    rows = []
    for text in out["text"].tolist():
        key = safe_text(text)
        res = cache.get(key)
        if res is None:
            res = analyze_text(key)
            res["tokens"] = content_tokens(res["norm"])
            cache[key] = res
        rows.append(res)

    out["norm"] = [r["norm"] for r in rows]
    out["tokens"] = [r["tokens"] for r in rows]
    out["risk"] = [r["risk"] for r in rows]
    out["level"] = [r["level"] for r in rows]
    out["label"] = [r["label"] for r in rows]
    for cat in C.RISK_CATEGORIES:
        out[f"skor_{cat}"] = [r["cat_scores"][cat] for r in rows]
    out["cues"] = [
        ", ".join(sorted({c["cue"] for c in r["cues"] if c["category"] in C.RISK_CATEGORIES and not c["negated"]}))
        for r in rows
    ]
    out["explanation"] = [r["explanation"] for r in rows]
    out["tni_relevant"] = [r["tni_relevant"] for r in rows]
    out["tni_target"] = [r["tni_target"] for r in rows]
    out["is_debunk"] = [r["is_debunk"] for r in rows]
    out["pii_phone"] = [r["pii"]["phone"] for r in rows]
    out["pii_nik"] = [r["pii"]["nik"] for r in rows]
    out["n_shorteners"] = [r["feats"]["n_shorteners"] for r in rows]
    out["n_hashtags"] = [r["feats"]["n_hashtags"] for r in rows]
    out["n_urls"] = [r["feats"]["n_urls"] for r in rows]

    out["reach"] = reach_score(
        out["likes"].to_numpy(), out["shares"].to_numpy(), out["replies"].to_numpy()
    )
    out["priority"] = priority_score(out["risk"].to_numpy(), out["reach"].to_numpy(), out["tni_target"].to_numpy())
    out["text_display"] = [mask_pii(t) for t in out["text"].tolist()]
    return out


def highlight_html(norm: str, cues: Iterable[dict]) -> str:
    """HTML aman (di-escape) dengan isyarat disorot. Hanya untuk teks ternormalisasi."""
    spans = []
    for c in cues:
        sp = c.get("span")
        if not sp or c["category"] not in C.RISK_CATEGORIES:
            continue
        spans.append((sp[0], sp[1], c["category"], c["negated"]))
    spans.sort()
    merged: list[tuple[int, int, str, bool]] = []
    for s, e, cat, neg in spans:
        if merged and s < merged[-1][1]:
            continue  # lewati tumpang tindih
        merged.append((s, e, cat, neg))
    out, pos = [], 0
    for s, e, cat, neg in merged:
        out.append(html.escape(norm[pos:s]))
        color = "#8A949B" if neg else C.CAT_COLORS.get(cat, "#E39B2D")
        title = html.escape(cat + (" (dinegasikan)" if neg else ""))
        out.append(
            f'<mark title="{title}" style="background:{color}33;border-bottom:2px solid {color};'
            f'color:inherit;padding:0 2px;border-radius:3px">{html.escape(norm[s:e])}</mark>'
        )
        pos = e
    out.append(html.escape(norm[pos:]))
    return "".join(out)
