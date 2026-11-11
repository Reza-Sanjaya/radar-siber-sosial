"""Utilitas teks: normalisasi bahasa Indonesia (slang, huruf berulang, leet),
fitur permukaan, token konten, dan masking data pribadi.

Semua fungsi aman terhadap nilai kosong / bukan string (hasilnya string kosong).
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Iterable

# --------------------------------------------------------------------------- #
# Pola dasar
# --------------------------------------------------------------------------- #
URL_RE = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|\b(?:bit\.ly|t\.co|tinyurl\.com|s\.id|cutt\.ly|wa\.me|t\.me|rb\.gy|shorturl\.at|linktr\.ee)/\S+",
    re.IGNORECASE,
)
SHORTENER_RE = re.compile(
    r"\b(?:bit\.ly|t\.co|tinyurl\.com|s\.id|cutt\.ly|rb\.gy|shorturl\.at)/\S+", re.IGNORECASE
)
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#(\w+)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+62|62|0)[\s\-]?8[\d\s\-]{7,13}\d(?!\d)")
NIK_RE = re.compile(r"(?<!\d)\d{16}(?!\d)")
ELONGATION_RE = re.compile(r"([^\W\d_])\1{2,}")  # hanya huruf; angka tidak diciutkan
LEET_RE = re.compile(r"(?<=[a-z])[0143578](?=[a-z])")
LEET_MAP = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"})
WORD_RE = re.compile(r"[a-z0-9']+")

# Slang / singkatan umum -> bentuk baku
SLANG = {
    "gak": "tidak", "ga": "tidak", "gk": "tidak", "nggak": "tidak", "ngga": "tidak",
    "enggak": "tidak", "tdk": "tidak", "tak": "tidak", "bkn": "bukan",
    "yg": "yang", "dgn": "dengan", "dg": "dengan", "utk": "untuk", "untk": "untuk",
    "sdh": "sudah", "udh": "sudah", "udah": "sudah", "blm": "belum", "krn": "karena",
    "karna": "karena", "jgn": "jangan", "jangn": "jangan", "bgt": "banget",
    "org": "orang", "orng": "orang", "dr": "dari", "sbg": "sebagai", "pd": "pada",
    "dlm": "dalam", "tp": "tapi", "tapi": "tapi", "klo": "kalau", "kalo": "kalau",
    "aja": "saja", "doang": "saja", "sj": "saja", "bs": "bisa", "bsa": "bisa",
    "lg": "lagi", "lgi": "lagi", "skrg": "sekarang", "skrng": "sekarang",
    "hrs": "harus", "dpt": "dapat", "kmrn": "kemarin", "bsk": "besok",
    "smua": "semua", "semuanya": "semua", "sy": "saya", "gue": "saya", "gw": "saya",
    "lu": "kamu", "lo": "kamu", "kmu": "kamu", "pls": "tolong", "tlg": "tolong",
    "tlong": "tolong", "pmrnth": "pemerintah", "pemrintah": "pemerintah",
    "hoax": "hoaks", "hoaxs": "hoaks", "hoaxes": "hoaks", "fake": "palsu",
    "share": "share", "sharekan": "sebarkan", "shareka": "sebarkan",
    "disebarluaskan": "disebarkan", "viralin": "viralkan", "sebarin": "sebarkan",
    "sebarkn": "sebarkan", "bgtu": "begitu", "emg": "memang", "emang": "memang",
    "trs": "terus", "trus": "terus", "kyk": "seperti", "kayak": "seperti",
    "spt": "seperti", "dll": "dan lain lain", "dsb": "dan sebagainya",
    "tni": "tni", "ad": "ad", "pak": "pak", "bu": "bu",
    "prajurit": "prajurit", "mrk": "mereka", "mereka": "mereka",
    "bnyk": "banyak", "banyaaak": "banyak", "kpd": "kepada", "ttg": "tentang",
    "ato": "atau", "atw": "atau", "ama": "sama", "sm": "sama",
}

STOPWORDS = frozenset(
    """
    yang dan di ke dari untuk pada dengan dalam adalah itu ini juga akan atau
    saya kamu kami kita mereka dia ia anda nya lah kah pun sudah belum telah sedang
    masih bisa dapat harus saja hanya tapi namun karena sebab jika kalau agar supaya
    sebagai oleh para ada tidak bukan ya yaa sih dong deh kok lho banget sangat
    lebih paling sangat semua setiap satu dua tiga lagi saat ketika sambil serta
    bagi tentang antara hingga sampai sejak seperti yaitu yakni dll dsb lain
    mau ingin tolong mohon mari ayo nih tuh aja gak ga ng pak bu mas mbak bang
    """.split()
)

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U00002B00-\U00002BFF]"
)


# --------------------------------------------------------------------------- #
# Pembantu
# --------------------------------------------------------------------------- #
def safe_text(value) -> str:
    """Ubah nilai apa pun menjadi string aman (NaN/None -> '')."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    try:
        text = str(value)
    except Exception:  # pragma: no cover - sangat jarang
        return ""
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    return text


def normalize(value, max_chars: int = 1500) -> str:
    """Normalisasi teks untuk pencocokan kamus.

    Langkah: NFKC, huruf kecil, URL & mention diganti token netral, huruf
    berulang diringkas ("heboooh" -> "heboh"), leet di antara huruf dipulihkan
    ("p3nipuan" -> "penipuan"), slang dibakukan, spasi dirapikan.
    """
    text = safe_text(value)[:max_chars]
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).lower()
    text = URL_RE.sub(" urltaut ", text)
    text = EMAIL_RE.sub(" emailref ", text)
    text = MENTION_RE.sub(" akunref ", text)
    text = text.replace("#", " ")
    text = ELONGATION_RE.sub(r"\1", text)
    text = LEET_RE.sub(lambda m: m.group(0).translate(LEET_MAP), text)
    # slang per token (pertahankan tanda baca)
    parts = re.split(r"(\W+)", text)
    parts = [SLANG.get(p, p) if p and p[0].isalnum() else p for p in parts]
    text = "".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def content_tokens(norm_text: str) -> list[str]:
    """Token konten (tanpa stopword, tanpa token netral) untuk kemiripan narasi."""
    tokens = []
    for tok in WORD_RE.findall(norm_text):
        if tok in STOPWORDS or tok in {"urltaut", "akunref", "emailref"}:
            continue
        if len(tok) < 3 or tok.isdigit():
            continue
        # stem sangat ringan agar "disebarkan" ~ "sebarkan"
        for suf in ("nya", "lah", "kah"):
            if tok.endswith(suf) and len(tok) - len(suf) >= 4:
                tok = tok[: -len(suf)]
                break
        if tok.startswith("di") and len(tok) > 6:
            tok = tok[2:]
        tokens.append(tok)
    return tokens


def extract_hashtags(value) -> list[str]:
    return [h.lower() for h in HASHTAG_RE.findall(safe_text(value))]


def surface_features(value) -> dict:
    """Fitur gaya penulisan dari teks asli (huruf kapital, tanda seru, URL, dll)."""
    text = safe_text(value)
    letters = [c for c in text if c.isalpha()]
    caps_ratio = 0.0
    if len(letters) >= 12:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    urls = URL_RE.findall(text)
    return {
        "caps_ratio": round(caps_ratio, 3),
        "exclaims": text.count("!"),
        "n_urls": len(urls),
        "n_shorteners": len(SHORTENER_RE.findall(text)),
        "n_mentions": len(MENTION_RE.findall(text)),
        "n_hashtags": len(HASHTAG_RE.findall(text)),
        "n_emoji": len(_EMOJI_RE.findall(text)),
        "n_words": len(text.split()),
    }


def find_pii(value) -> dict:
    """Deteksi data pribadi dalam teks (telepon, NIK 16 digit, email)."""
    text = safe_text(value)
    return {
        "phone": len(PHONE_RE.findall(text)),
        "nik": len(NIK_RE.findall(text)),
        "email": len(EMAIL_RE.findall(text)),
    }


def mask_pii(value, mask_mentions: bool = False) -> str:
    """Samarkan data pribadi pada teks yang akan ditampilkan / diekspor."""
    text = safe_text(value)
    if not text:
        return ""

    def _phone(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return digits[:4] + "-****-****"

    def _nik(m: re.Match) -> str:
        return m.group(0)[:4] + "************"

    text = NIK_RE.sub(_nik, text)
    text = PHONE_RE.sub(_phone, text)
    text = EMAIL_RE.sub("[email]", text)
    if mask_mentions:
        text = MENTION_RE.sub("@[akun]", text)
    return text


def mask_pii_keep_length(value, keep: int = 4) -> str:
    """Samarkan NIK/telepon dengan tanda * TANPA mengubah panjang teks.

    Dipakai untuk menampilkan teks ternormalisasi: posisi karakter tetap sama sehingga
    sorotan isyarat (berbasis indeks) tidak bergeser.
    """
    text = safe_text(value)

    def _mask(m: re.Match) -> str:
        seen = 0
        out = []
        for ch in m.group(0):
            if ch.isdigit():
                seen += 1
                out.append(ch if seen <= keep else "*")
            else:
                out.append(ch)
        return "".join(out)

    text = NIK_RE.sub(_mask, text)
    return PHONE_RE.sub(_mask, text)


def word_shingles(tokens: list[str], k: int = 3) -> set[str]:
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: Iterable, b: Iterable) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0
