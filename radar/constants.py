"""Konstanta bersama: kategori, level, warna, batas aman."""
from __future__ import annotations

APP_NAME = "Radar Siber Sosial"
APP_TAGLINE = "Deteksi dini ancaman non-teknis di ruang siber sosial"

# ---- Kategori konten -------------------------------------------------------
CAT_DISINFO = "Disinformasi"
CAT_PROVOKASI = "Provokasi/SARA"
CAT_KEKERASAN = "Kebencian/Kekerasan"
CAT_PENIPUAN = "Penipuan/Phishing"
CAT_DOXXING = "Doxxing/Data Pribadi"
CAT_KLARIFIKASI = "Klarifikasi/Cek Fakta"
CAT_NETRAL = "Netral"

RISK_CATEGORIES = [CAT_DISINFO, CAT_PROVOKASI, CAT_KEKERASAN, CAT_PENIPUAN, CAT_DOXXING]
ALL_LABELS = RISK_CATEGORIES + [CAT_KLARIFIKASI, CAT_NETRAL]

# Bobot tiap kategori pada penggabungan "noisy-OR"
CATEGORY_WEIGHT = {
    CAT_DISINFO: 0.85,
    CAT_PROVOKASI: 0.90,
    CAT_KEKERASAN: 1.00,
    CAT_PENIPUAN: 0.90,
    CAT_DOXXING: 0.90,
}

CAT_COLORS = {
    CAT_DISINFO: "#E39B2D",
    CAT_PROVOKASI: "#C94F7C",
    CAT_KEKERASAN: "#D64545",
    CAT_PENIPUAN: "#8E6BD1",
    CAT_DOXXING: "#3C9BD1",
    CAT_KLARIFIKASI: "#2E9E6B",
    CAT_NETRAL: "#8A949B",
}

# ---- Level risiko konten ---------------------------------------------------
RISK_LEVELS = [  # (nama, batas bawah)
    ("Rendah", 0.0),
    ("Sedang", 25.0),
    ("Tinggi", 50.0),
    ("Kritis", 75.0),
]
LEVEL_COLORS = {
    "Rendah": "#2E9E6B",
    "Sedang": "#D9A62E",
    "Tinggi": "#E8782B",
    "Kritis": "#D64545",
}

# ---- Status Indeks Siber Sosial (ISS) --------------------------------------
STATUS_LEVELS = [
    ("AMAN", 0.0),
    ("WASPADA", 25.0),
    ("SIAGA", 50.0),
    ("AWAS", 75.0),
]
STATUS_COLORS = {
    "AMAN": "#2E9E6B",
    "WASPADA": "#D9A62E",
    "SIAGA": "#E8782B",
    "AWAS": "#D64545",
}

# ---- Ambang & batas --------------------------------------------------------
DEFAULT_HIGH_RISK = 50.0        # skor >= ini dianggap "berisiko tinggi"
BINARY_RISK_THRESHOLD = 40.0    # dipakai pada evaluasi biner (berisiko / aman)
DEFAULT_SIM_THRESHOLD = 0.55    # kemiripan Jaccard minimal untuk satu narasi
DEFAULT_MIN_CLUSTER = 3         # ukuran minimal narasi
COORD_STRONG = 70.0
COORD_INDICATION = 45.0

MAX_ROWS = 20000                # batas baris yang dianalisis
MAX_TEXT_CHARS = 1500           # teks dipotong agar analisis tetap cepat
MIN_TOKENS_FOR_CLUSTER = 3


def risk_level(score: float) -> str:
    """Konversi skor 0-100 menjadi nama level risiko."""
    name = RISK_LEVELS[0][0]
    for lvl, low in RISK_LEVELS:
        if score >= low:
            name = lvl
    return name


def status_level(score: float) -> str:
    """Konversi ISS 0-100 menjadi status peringatan."""
    name = STATUS_LEVELS[0][0]
    for lvl, low in STATUS_LEVELS:
        if score >= low:
            name = lvl
    return name
