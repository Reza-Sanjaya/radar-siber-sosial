"""Pemuatan, validasi, dan anonimisasi data CSV.

Prinsip perlindungan data (selaras UU PDP & ketentuan lomba):
  * identitas akun diganti alias (hash) secara default
  * @mention pada teks diganti "@[akun]" saat anonimisasi aktif
  * nomor telepon / NIK / email disamarkan pada teks yang ditampilkan/diekspor
  * aplikasi TIDAK melakukan scraping; hanya memproses CSV yang diunggah pengguna
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import constants as C
from .text_utils import MENTION_RE, safe_text

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = BASE_DIR / "data" / "sample_posts.csv"
EVAL_PATH = BASE_DIR / "data" / "eval_set.csv"

REQUIRED = ["timestamp", "account_id", "text"]
NUMERIC_OPTIONAL = ["likes", "shares", "replies", "followers", "following", "account_age_days"]
ALL_COLUMNS = ["post_id", "timestamp", "platform", "account_id", "text"] + NUMERIC_OPTIONAL

ALIASES = {
    "timestamp": ["timestamp", "waktu", "tanggal", "created_at", "date", "datetime", "time", "tgl", "waktu_posting"],
    "account_id": ["account_id", "akun", "username", "user", "user_id", "author", "screen_name", "id_akun", "nama_akun"],
    "text": ["text", "teks", "konten", "content", "isi", "tweet", "caption", "post", "komentar_teks", "pesan"],
    "platform": ["platform", "sumber", "source", "kanal"],
    "post_id": ["post_id", "id", "id_post", "tweet_id", "status_id"],
    "likes": ["likes", "suka", "like_count", "favorite_count", "favorites", "jumlah_suka"],
    "shares": ["shares", "retweets", "repost", "reposts", "share_count", "retweet_count", "bagikan", "jumlah_share"],
    "replies": ["replies", "komentar", "reply_count", "comments", "comment_count", "balasan"],
    "followers": ["followers", "pengikut", "follower_count", "jumlah_pengikut"],
    "following": ["following", "mengikuti", "friends_count", "following_count", "jumlah_mengikuti"],
    "account_age_days": ["account_age_days", "umur_akun_hari", "usia_akun_hari", "umur_akun", "usia_akun"],
}


@dataclass
class LoadResult:
    df: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    n_rows_in: int = 0

    @property
    def ok(self) -> bool:
        return self.df is not None and not self.errors


# --------------------------------------------------------------------------- #
# Membaca CSV mentah
# --------------------------------------------------------------------------- #
def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Baca CSV dari bytes: coba beberapa encoding & deteksi pemisah otomatis."""
    if not data or not data.strip():
        raise ValueError("File kosong.")
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError as exc:
            last_err = exc
            continue
        try:
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", on_bad_lines="skip", dtype=str)
        except Exception as exc:  # pemisah tak terdeteksi, dsb.
            last_err = exc
            try:
                df = pd.read_csv(io.StringIO(text), sep=",", engine="python", on_bad_lines="skip", dtype=str)
            except Exception as exc2:
                last_err = exc2
                continue
        return df
    raise ValueError(f"File tidak dapat dibaca sebagai CSV ({last_err}).")


def _canon(name) -> str:
    n = str(name).strip().lower().replace("﻿", "")
    n = re.sub(r"[\s\-/]+", "_", n)
    return n


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    lookup = {}
    for canon, names in ALIASES.items():
        for n in names:
            lookup.setdefault(n, canon)
    rename = {}
    used: set[str] = set()
    for col in df.columns:
        canon = lookup.get(_canon(col))
        if canon and canon not in used:
            rename[col] = canon
            used.add(canon)
    out = df.rename(columns=rename)
    keep = [c for c in out.columns if c in ALL_COLUMNS]
    return out[keep].copy()


def _parse_timestamps(series: pd.Series) -> pd.Series:
    """Parse waktu -> datetime naif (WIB). Zona waktu eksplisit dikonversi ke WIB."""
    s = series.astype("string")
    numeric = pd.to_numeric(s, errors="coerce")
    if numeric.notna().mean() > 0.9:  # epoch
        unit = "ms" if float(numeric.dropna().abs().median()) > 1e11 else "s"
        ts = pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
        return ts.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    parsed = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
    has_tz = s.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})\s*$", regex=True, na=False)
    wib = parsed.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    naive = parsed.dt.tz_localize(None)
    return wib.where(has_tz, naive)


def alias_for(account: str, salt: str = "radar") -> str:
    digest = hashlib.sha256(f"{salt}|{account}".encode("utf-8")).hexdigest()[:6].upper()
    return f"AKUN-{digest}"


# --------------------------------------------------------------------------- #
# Standardisasi
# --------------------------------------------------------------------------- #
def standardize(df_raw: pd.DataFrame, anonymize: bool = True, salt: str = "radar") -> LoadResult:
    res = LoadResult(n_rows_in=0 if df_raw is None else len(df_raw))
    if df_raw is None or len(df_raw) == 0:
        res.errors.append("Data kosong: tidak ada baris untuk dianalisis.")
        return res

    df = _map_columns(df_raw)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        found = ", ".join(map(str, df_raw.columns[:12])) or "(tidak ada)"
        res.errors.append(
            "Kolom wajib tidak ditemukan: " + ", ".join(missing)
            + f". Kolom yang terbaca: {found}. Unduh template CSV pada halaman Data & Laporan."
        )
        return res

    # teks
    df["text"] = df["text"].map(lambda v: safe_text(v).strip()[: C.MAX_TEXT_CHARS])
    n0 = len(df)
    df = df[df["text"].str.len() > 0].copy()
    if len(df) < n0:
        res.warnings.append(f"{n0 - len(df)} baris tanpa teks dibuang.")

    # waktu
    df["timestamp"] = _parse_timestamps(df["timestamp"])
    n0 = len(df)
    df = df[df["timestamp"].notna()].copy()
    if len(df) < n0:
        res.warnings.append(f"{n0 - len(df)} baris dengan format waktu tidak valid dibuang.")
    if len(df) == 0:
        res.errors.append("Tidak ada baris dengan waktu yang valid. Gunakan format seperti 2026-11-01 14:30:00.")
        return res

    # akun
    df["account_id"] = df["account_id"].map(lambda v: safe_text(v).strip())
    blank = df["account_id"] == ""
    if blank.any():
        res.warnings.append(f"{int(blank.sum())} baris tanpa akun diberi label 'tidak_diketahui'.")
        df.loc[blank, "account_id"] = "tidak_diketahui"

    # kolom opsional
    if "platform" not in df.columns:
        df["platform"] = "Tidak diketahui"
    df["platform"] = df["platform"].map(lambda v: safe_text(v).strip() or "Tidak diketahui")
    for col in NUMERIC_OPTIONAL:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce").clip(lower=0)
    for col in ("likes", "shares", "replies"):
        df[col] = df[col].fillna(0.0)

    # post_id unik
    if "post_id" not in df.columns:
        df["post_id"] = [f"P{i:06d}" for i in range(1, len(df) + 1)]
    else:
        df["post_id"] = df["post_id"].map(lambda v: safe_text(v).strip())
        empty_id = df["post_id"] == ""
        df.loc[empty_id, "post_id"] = [f"AUTO{i:06d}" for i in range(int(empty_id.sum()))]
        dup = df["post_id"].duplicated(keep="first")
        if dup.any():
            res.warnings.append(f"{int(dup.sum())} baris dengan post_id ganda dibuang (ambil yang pertama).")
            df = df[~dup].copy()

    # batas baris: ambil yang terbaru
    if len(df) > C.MAX_ROWS:
        res.warnings.append(
            f"Data {len(df):,} baris melebihi batas {C.MAX_ROWS:,}; hanya {C.MAX_ROWS:,} baris terbaru dianalisis."
        )
        df = df.sort_values("timestamp").tail(C.MAX_ROWS).copy()

    # anonimisasi
    if anonymize:
        df["account_id"] = df["account_id"].map(lambda a: alias_for(a, salt))
        df["text"] = df["text"].map(lambda t: MENTION_RE.sub("@[akun]", t))

    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    df = df[ALL_COLUMNS]
    res.df = df
    return res


def load_csv_bytes(data: bytes, anonymize: bool = True, salt: str = "radar") -> LoadResult:
    """Pintu masuk untuk berkas unggahan: baca + standardisasi, tanpa melempar exception."""
    try:
        raw = read_csv_bytes(data)
    except Exception as exc:
        r = LoadResult()
        r.errors.append(str(exc))
        return r
    return standardize(raw, anonymize=anonymize, salt=salt)


def load_sample() -> LoadResult:
    """Muat data sintetis bawaan (fiktif)."""
    if not SAMPLE_PATH.exists():
        from .synth import generate_posts  # bangkitkan di memori bila berkas hilang

        return standardize(generate_posts(seed=2026), anonymize=False)
    return load_csv_bytes(SAMPLE_PATH.read_bytes(), anonymize=False)


def template_csv_bytes() -> bytes:
    """Template CSV (berisi contoh fiktif) untuk diunduh pengguna."""
    rows = [
        ["P000001", "2026-11-01 08:15:00", "X", "akun_contoh_1", "Contoh teks unggahan pertama (fiktif).", 12, 3, 1, 250, 180, 420],
        ["P000002", "2026-11-01 09:40:00", "Facebook", "akun_contoh_2", "Contoh teks lain untuk uji coba.", 0, 0, 0, 40, 900, 12],
    ]
    cols = ["post_id", "timestamp", "platform", "account_id", "text", "likes", "shares", "replies",
            "followers", "following", "account_age_days"]
    buf = io.StringIO()
    pd.DataFrame(rows, columns=cols).to_csv(buf, index=False)
    return ("﻿" + buf.getvalue()).encode("utf-8")
