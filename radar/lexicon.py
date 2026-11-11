"""Kamus isyarat (cue) untuk analisis konten - transparan dan dapat diaudit.

Setiap entri berbentuk (frasa, bobot). Aturan penulisan frasa:
    "kata kata"   -> cocok sebagai frasa utuh (batas kata)
    "*bunuh*"     -> awalan/akhiran bebas (membunuh, dibunuh, pembunuhan)
    "re:<regex>"  -> regex mentah
Bobot positif = menambah risiko, negatif = isyarat kredibilitas.

Catatan metodologi: kamus ini adalah *isyarat* untuk memprioritaskan tinjauan
manusia, bukan penentu kebenaran sebuah informasi.
"""
from __future__ import annotations

import re
from typing import Iterable

from . import constants as C


def _compile(entries: Iterable[tuple[str, float]]) -> list[tuple[re.Pattern, float, str]]:
    compiled = []
    for phrase, weight in entries:
        label = None
        if phrase.startswith("re:"):
            pattern = phrase[3:]
            if "=>" in pattern:  # "re:<regex>=><label yang tampil ke pengguna>"
                pattern, label = pattern.rsplit("=>", 1)
            else:
                label = pattern
        else:
            lead = r"\b\w*" if phrase.startswith("*") else r"\b"
            trail = r"\w*\b" if phrase.endswith("*") else r"\b"
            core = phrase.strip("*")
            body = r"\s+".join(re.escape(p) for p in core.split())
            pattern = lead + body + trail
        compiled.append((re.compile(pattern), float(weight), label or phrase.strip("*")))
    return compiled


# --------------------------------------------------------------------------- #
# DISINFORMASI / HOAKS
# --------------------------------------------------------------------------- #
_DISINFO = [
    ("viral", 0.5), ("heboh", 0.7),
    ("sebarkan", 1.2), ("viralkan", 1.2), ("segera sebar*", 1.2),
    ("bagikan ke semua", 1.2), ("share ke semua", 1.2), ("share sebanyak", 1.2),
    ("forward ke", 0.8), ("tolong sebar*", 1.0), ("sebarkan seluas", 1.4),
    ("jangan percaya media", 1.8), ("media bungkam", 1.8), ("media tidak berani", 1.6),
    ("media mainstream", 0.9), ("ditutup tutupi", 1.6), ("disembunyikan", 1.2),
    ("tidak diberitakan", 1.2), ("pemerintah menutupi", 1.8), ("konspirasi", 1.2),
    ("rekayasa", 0.9), ("settingan", 1.0), ("dalang", 0.9),
    ("katanya", 0.8), ("konon", 0.9), ("kabarnya", 0.8), ("kabar burung", 1.2),
    ("bocoran", 1.0), ("info rahasia", 1.3), ("rahasia besar", 1.3),
    ("terbongkar", 1.2), ("akhirnya terungkap", 1.2), ("fakta mengejutkan", 1.3),
    ("mengejutkan", 0.6), ("tidak banyak yang tahu", 0.9),
    ("sumber terpercaya", 1.0), ("sumber dalam", 1.2), ("orang dalam", 1.2),
    ("teman saya yang bekerja", 1.4), ("saudara saya yang bekerja", 1.4),
    ("dijamin benar", 1.5), ("100 benar", 1.4), ("pasti benar", 1.2),
    ("bukan hoaks", 1.5), ("ini bukan hoaks", 1.5),
    ("sebelum dihapus", 1.6), ("sebelum diblokir", 1.6), ("akan dihapus", 1.0),
    ("darurat", 0.7), ("peringatan penting", 0.8), ("waspada", 0.4), ("segera", 0.4),
    ("hari ini juga", 0.4),
    ("pasukan asing", 1.4), ("invasi", 1.0), ("kudeta", 1.4), ("darurat militer", 1.6),
    ("perang saudara", 1.4), ("chaos", 0.8), ("negara akan bubar", 1.5),
    ("negara hancur", 1.0), ("ditutup permanen", 1.0), ("dibubarkan", 0.8),
    ("posko ditutup", 1.2), ("bantuan dihentikan", 1.0), ("bantuan ditahan", 1.0),
    ("dikorupsi", 0.9), ("diselewengkan", 0.9),
]

# Isyarat kredibilitas (menurunkan skor disinformasi)
_CREDIBILITY = [
    ("rilis resmi", -0.8), ("siaran pers", -0.8), ("pernyataan resmi", -0.8),
    ("keterangan resmi", -0.8), ("dikonfirmasi", -0.6), ("berdasarkan data", -0.6),
    ("menurut data", -0.6), (r"re:\bsumber\s*:=>rujukan sumber", -0.7), ("tautan sumber", -0.5),
    ("kanal resmi", -0.6), ("akun resmi", -0.5),
]

# Konten klarifikasi / cek fakta (benign) - dipakai untuk menahan false positive
_DEBUNK = [
    ("cek fakta", 1.0), ("klarifikasi", 1.0), ("tidak benar", 1.0), ("hoaks", 1.0),
    ("disinformasi", 1.0), ("kabar bohong", 1.0), ("berita bohong", 1.0),
    ("bukan fakta", 1.0), ("faktanya", 0.8), ("mohon tidak menyebarkan", 1.0),
    ("mohon tidak menyebar", 1.0), ("jangan sebarkan", 1.0), ("kami bantah", 1.0),
    ("dibantah", 0.8), ("meluruskan", 0.8), ("luruskan", 0.8), ("informasi keliru", 1.0),
    ("tidak ada kebenaran", 1.0), ("tidak berdasar", 0.8), ("waspada penipuan", 0.8),
]
_DEBUNK_NEGATE_RE = re.compile(r"\b(?:bukan|tidak|jangan sebut)\s+hoaks")

# --------------------------------------------------------------------------- #
# PROVOKASI / SARA / ADU DOMBA / MOBILISASI
# --------------------------------------------------------------------------- #
_PROVOKASI = [
    ("adu domba", 1.0), ("pecah belah", 1.0), ("benturkan", 1.0), ("dibenturkan", 1.0),
    ("antek", 1.2), ("antek asing", 1.5), ("pengkhianat", 1.3), ("musuh bersama", 1.2),
    ("musuh", 0.6), ("penjajah", 1.0), ("perusak negeri", 1.0), ("biang kerok", 0.9),
    ("usir", 1.0), ("diusir", 1.0), ("boikot", 0.7), ("bangkit melawan", 1.2),
    ("kita atau mereka", 1.2), ("mereka bukan bagian dari kita", 1.5),
    ("bukan orang kita", 1.0), ("tidak pantas hidup", 2.0),
    ("hama", 0.9), ("sampah masyarakat", 1.3), ("parasit", 0.9), ("kecoa", 1.2),
    ("binatang", 0.9), ("turun ke jalan", 0.8), ("aksi massa", 0.7),
    ("ayo bergerak", 0.8), ("saatnya bergerak", 0.8), ("kumpul di", 0.4),
    ("tidak layak tinggal", 1.4), ("angkat kaki", 1.0), ("pulang ke", 0.5),
    ("dibiarkan saja", 0.3), ("sudah saatnya kita", 0.6),
]
# Penanda identitas (tidak dinilai sendiri; hanya memicu aturan ko-okurensi)
_IDENTITY = [
    ("agama", 1), ("suku", 1), ("etnis", 1), ("ras", 1), ("umat", 1), ("pribumi", 1),
    ("asing", 1), ("golongan", 1), ("islam", 1), ("muslim", 1),
    ("kristen", 1), ("katolik", 1), ("hindu", 1), ("buddha", 1), ("konghucu", 1),
    ("mayoritas", 1), ("minoritas", 1), ("warga pendatang", 1), ("pendatang", 1),
]

# --------------------------------------------------------------------------- #
# KEBENCIAN / KEKERASAN
# --------------------------------------------------------------------------- #
_KEKERASAN = [
    ("*bunuh*", 2.0), ("*bantai*", 2.2), ("*habisi*", 2.0), ("*basmi*", 2.0),
    ("bakar rumah", 2.0), ("bakar markas", 2.2), ("bakar kantor", 2.0), ("bakar mereka", 2.2),
    ("bakar", 0.3), ("hancurkan", 1.4), ("*penggal*", 2.2), ("*musnahkan*", 1.8),
    ("ganyang", 2.0), ("libas", 1.4), ("sapu bersih", 1.4), ("serbu", 1.4),
    ("serang", 1.0), ("kepung", 1.2), ("geruduk", 1.2), ("halal darah", 2.5),
    ("darah mereka", 2.0), ("angkat senjata", 1.8), ("gantung", 1.0),
    ("tembak", 0.8), ("hajar", 1.0), ("lempar batu", 1.4), (r"re:\b(?:memukul\w*|dipukul\w*|pemukulan|pukuli|pukul\s+(?:dia|mereka|saja|dengan|kepala|wajah|muka))\b=>memukul", 0.5),
    ("mati saja", 1.6), ("pantas mati", 2.0), ("lenyapkan", 2.0),
]
_CTA = [  # ajakan bertindak; menaikkan kekerasan bila ko-okuren
    ("ayo", 1), ("mari", 1), ("saatnya", 1), ("waktunya", 1), ("bergerak", 1),
    ("serentak", 1), ("rame rame", 1), ("ramai ramai", 1),
]

# --------------------------------------------------------------------------- #
# PENIPUAN / PHISHING / REKAYASA SOSIAL
# --------------------------------------------------------------------------- #
_PENIPUAN = [
    ("klik link", 0.8), ("klik tautan", 0.8), ("klik di sini", 1.0), ("klik disini", 1.0),
    ("hubungi admin", 1.0), ("hubungi wa", 0.8), ("transfer", 0.6), ("rekening", 0.6),
    ("biaya administrasi", 1.0), ("biaya pendaftaran", 0.8), ("biaya seleksi", 1.0),
    ("hadiah", 0.8), ("selamat anda", 1.2), ("anda menang", 1.5), ("anda terpilih", 1.4),
    ("undian", 1.0), ("gratis", 0.4), ("kuota gratis", 1.3), ("bagi bagi", 0.5),
    ("bantuan tunai", 0.9), ("verifikasi akun", 1.5), ("akun anda diblokir", 1.8),
    ("akun anda akan", 1.0), ("login", 0.3), ("kode otp", 1.0), ("otp", 0.6),
    ("password", 0.3), ("kata sandi", 0.3), ("pin atm", 1.2),
    (r"re:\b(?:kirim|berikan|beri|masukkan|bagikan|sebutkan)\w*\s+(?:\w+\s+){0,2}(?:otp|password|kata sandi|pin|kode)\b=>meminta/mengirim OTP, PIN, atau kata sandi", 2.0), ("judi online", 1.5),
    ("slot gacor", 1.8), ("togel", 1.5), ("slot", 0.4), ("pinjol", 1.2),
    ("pinjaman cepat", 1.2), ("tanpa jaminan", 0.8), ("modal receh", 1.0),
    ("download apk", 1.8), ("file apk", 1.6), ("install apk", 1.8), ("pasang aplikasi", 0.8),
    ("lulus tanpa tes", 2.0), ("jalur khusus", 1.0), ("jalur belakang", 1.2), ("calo", 1.4),
    ("uang pelicin", 1.5), ("pasti lulus", 1.6), ("jaminan lulus", 1.8), ("jalur dalam", 1.2),
    ("investasi cepat", 1.2), ("untung pasti", 1.5), ("profit harian", 1.3),
]

# --------------------------------------------------------------------------- #
# DOXXING / PEMBOCORAN DATA PRIBADI
# --------------------------------------------------------------------------- #
_DOXXING = [
    ("alamat lengkap", 1.2), ("alamat rumah", 1.2), ("no hp", 0.6), ("nomor hp", 0.6),
    ("nomor telepon", 0.5), ("data pribadi", 0.8), ("foto ktp", 1.8), ("kartu keluarga", 1.0),
    ("nik", 0.8), ("bocoran data", 1.2), ("sebar data", 1.5), ("doxing", 2.0), ("dox", 2.0),
    ("doxxing", 2.0), ("ayo cari", 1.0), ("tempat tinggal", 1.0), ("sekolah anaknya", 1.6),
    ("anaknya sekolah di", 1.6), ("viralkan identitas", 2.0), ("identitas lengkap", 1.4),
    ("identitasnya", 0.8), ("sebarkan alamat", 2.0), ("telanjangi", 1.5), ("kita cari tahu", 0.8),
]
# Kata pemicu agar nomor telepon dianggap sebagai doxxing (bukan sekadar kontak)
DOXX_CONTEXT_RE = re.compile(
    r"\b(?:alamat|rumah|ktp|nik|data pribadi|sebar\w*|geruduk|cari|identitas|anaknya|sekolah)\b"
)

# --------------------------------------------------------------------------- #
# RELEVANSI INSTITUSI (TNI AD / satuan) & REKRUTMEN
# --------------------------------------------------------------------------- #
_INSTITUSI = [
    ("tni ad", 1), ("tni", 1), ("angkatan darat", 1), ("tentara", 1), ("prajurit", 1),
    ("markas", 1), ("kodam", 1), ("korem", 1), ("kodim", 1), ("koramil", 1),
    ("batalyon", 1), ("alutsista", 1), ("panglima", 1), ("kasad", 1), ("satuan", 1),
    ("bintara", 1), ("pussiberad", 1), ("posko", 1),
]
RECRUIT_RE = re.compile(r"\b(?:rekrutmen|pendaftaran|seleksi|penerimaan|bintara|akmil|secaba|tamtama)\b")
PAYMENT_RE = re.compile(
    r"\b(?:bayar|transfer|biaya|uang|jalur khusus|calo|titip|setor|rekening|pelicin)\b"
)

NEGATORS = frozenset(
    {"jangan", "tidak", "bukan", "stop", "tolak", "kecam", "mengecam", "anti", "tanpa",
     "menolak", "dilarang", "hindari", "waspada", "lawan"}
)

# --------------------------------------------------------------------------- #
# Hasil kompilasi (dipakai analyzer)
# --------------------------------------------------------------------------- #
DISINFO = _compile(_DISINFO)
CREDIBILITY = _compile(_CREDIBILITY)
DEBUNK = _compile(_DEBUNK)
PROVOKASI = _compile(_PROVOKASI)
IDENTITY = _compile(_IDENTITY)
KEKERASAN = _compile(_KEKERASAN)
CTA = _compile(_CTA)
PENIPUAN = _compile(_PENIPUAN)
DOXXING = _compile(_DOXXING)
INSTITUSI = _compile(_INSTITUSI)
DEBUNK_NEGATE_RE = _DEBUNK_NEGATE_RE

CATEGORY_LEXICONS = {
    C.CAT_DISINFO: DISINFO,
    C.CAT_PROVOKASI: PROVOKASI,
    C.CAT_KEKERASAN: KEKERASAN,
    C.CAT_PENIPUAN: PENIPUAN,
    C.CAT_DOXXING: DOXXING,
}

# Kategori yang sensitif terhadap negasi ("jangan bunuh", "kami kecam kekerasan")
NEGATION_SENSITIVE = set(CATEGORY_LEXICONS)


def lexicon_summary() -> dict[str, int]:
    """Jumlah isyarat per kategori (untuk halaman Tentang)."""
    out = {name: len(entries) for name, entries in CATEGORY_LEXICONS.items()}
    out["Kredibilitas"] = len(CREDIBILITY)
    out["Klarifikasi"] = len(DEBUNK)
    out["Penanda identitas"] = len(IDENTITY)
    out["Penanda institusi"] = len(INSTITUSI)
    return out
