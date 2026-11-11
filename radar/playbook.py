"""Rekomendasi tindakan (human-in-the-loop) & draf klarifikasi.

Sistem TIDAK mengambil tindakan otomatis (tidak menghapus, melaporkan, atau
menyerang akun mana pun). Seluruh rekomendasi adalah saran bagi petugas dan
harus disesuaikan dengan SOP, kewenangan, dan perizinan satuan masing-masing.
"""
from __future__ import annotations

from . import constants as C

SLA = {
    "Kritis": "Tindak lanjut maksimal 1 jam",
    "Tinggi": "Tindak lanjut maksimal 4 jam",
    "Sedang": "Tinjau dalam 24 jam",
    "Rendah": "Pantau rutin",
}

_BASE_STEPS = [
    "Simpan bukti: tangkapan layar, URL, alias akun, dan waktu unggah (jangan diubah).",
    "Verifikasi manual oleh petugas sebelum mengambil keputusan; skor sistem hanya prioritas tinjauan.",
]

PLAYBOOK = {
    C.CAT_DISINFO: {
        "unit": "Fungsi penerangan/humas + fungsi siber satuan",
        "steps": [
            "Verifikasi klaim ke sumber resmi/fungsi terkait (tanggal, lokasi, pelaku, dokumen).",
            "Siapkan klarifikasi singkat berbasis fakta dan tautan sumber resmi.",
            "Publikasikan klarifikasi melalui kanal resmi; hindari menyebut ulang klaim palsu tanpa konteks.",
            "Pantau penyebaran narasi selama 24 jam dan ukur apakah klarifikasi menurunkan laju.",
        ],
        "template": (
            "KLARIFIKASI\n\n"
            "Beredar informasi mengenai [ISU]. Informasi tersebut TIDAK BENAR.\n\n"
            "Fakta: [FAKTA_RESMI]\n\n"
            "Sumber resmi: [SUMBER_RESMI]. Mohon tidak menyebarkan informasi yang belum terverifikasi. "
            "Informasi terbaru akan disampaikan melalui [KANAL_RESMI]."
        ),
    },
    C.CAT_PROVOKASI: {
        "unit": "Fungsi penerangan + fungsi pengamanan/intelijen (sesuai SOP) + pimpinan satuan",
        "steps": [
            "Nilai potensi eskalasi di dunia nyata (ajakan berkumpul, lokasi, waktu).",
            "Hindari membalas provokasi secara emosional; gunakan narasi persatuan yang faktual.",
            "Laporkan konten bermuatan SARA ke platform melalui fitur pelaporan resmi.",
            "Koordinasikan dengan pimpinan satuan bila ada ajakan aksi fisik.",
        ],
        "template": (
            "IMBAUAN\n\n"
            "Kami mengajak masyarakat menjaga persatuan dan tidak terpancing isu yang memecah belah terkait [ISU]. "
            "Mohon verifikasi informasi melalui [KANAL_RESMI] sebelum membagikannya."
        ),
    },
    C.CAT_KEKERASAN: {
        "unit": "Pimpinan satuan + fungsi pengamanan/intelijen (sesuai SOP) + pihak berwenang",
        "steps": [
            "Eskalasi segera ke pimpinan; ajakan kekerasan harus ditangani sebagai prioritas tertinggi.",
            "Laporkan konten ke platform dan, bila perlu, ke pihak berwenang sesuai prosedur.",
            "Jangan membalas atau mendatangi pelaku; jaga keselamatan petugas.",
            "Dokumentasikan seluruh bukti untuk proses lanjutan.",
        ],
        "template": (
            "PERNYATAAN\n\n"
            "Kami mengecam segala bentuk ajakan kekerasan terkait [ISU]. "
            "Persoalan harus diselesaikan melalui jalur hukum yang berlaku. Informasi resmi: [KANAL_RESMI]."
        ),
    },
    C.CAT_PENIPUAN: {
        "unit": "Fungsi siber/TI satuan + fungsi penerangan",
        "steps": [
            "Jangan mengklik tautan; analisis tautan hanya di lingkungan terisolasi oleh petugas siber.",
            "Laporkan akun/tautan ke platform dan penyedia domain; catat indikator (domain, nomor rekening).",
            "Terbitkan peringatan publik: institusi tidak memungut biaya di luar kanal resmi.",
            "Bila mencatut nama institusi/rekrutmen, sampaikan alur resmi yang benar.",
        ],
        "template": (
            "WASPADA PENIPUAN\n\n"
            "Beredar pesan yang mengatasnamakan [ISU]. Pesan tersebut BUKAN dari kami. "
            "Proses resmi tidak memungut biaya melalui rekening pribadi dan hanya diumumkan di [KANAL_RESMI]. "
            "Jangan mengklik tautan atau mentransfer uang."
        ),
    },
    C.CAT_DOXXING: {
        "unit": "Fungsi hukum + fungsi siber satuan + pihak yang terdampak",
        "steps": [
            "Hubungi pihak yang datanya bocor (dengan persetujuan) dan sarankan pengamanan akun.",
            "Laporkan unggahan ke platform dengan dasar pelanggaran privasi.",
            "Jangan menyalin atau menyebarkan ulang data pribadi, termasuk saat pelaporan internal.",
            "Pertimbangkan langkah hukum sesuai UU Pelindungan Data Pribadi.",
        ],
        "template": (
            "IMBAUAN PERLINDUNGAN DATA\n\n"
            "Kami mengimbau agar tidak menyebarkan data pribadi pihak mana pun terkait [ISU]. "
            "Penyebaran data pribadi dapat berdampak hukum. Laporkan melalui [KANAL_RESMI]."
        ),
    },
    C.CAT_KLARIFIKASI: {
        "unit": "Fungsi penerangan/humas",
        "steps": [
            "Konten ini mendukung literasi; pertimbangkan untuk memperkuat jangkauannya.",
            "Pastikan fakta dan tautan sumber akurat sebelum dibagikan ulang.",
        ],
        "template": "",
    },
    C.CAT_NETRAL: {
        "unit": "-",
        "steps": ["Tidak perlu tindakan khusus; pantau secara rutin."],
        "template": "",
    },
}

EXTRA_COORDINATED = [
    "Kumpulkan daftar akun (alias), waktu unggah, dan kesamaan teks sebagai bukti koordinasi.",
    "Jangan membalas akun-akun tersebut secara langsung agar narasi tidak ikut teramplifikasi.",
    "Ajukan laporan perilaku terkoordinasi ke platform melalui kanal pelaporan resmi.",
]
EXTRA_INSTITUTION = [
    "Libatkan pimpinan satuan karena narasi menyasar nama institusi/satuan.",
]
DONTS = [
    "Jangan melakukan doxxing balasan atau serangan siber terhadap akun mana pun.",
    "Jangan menghapus atau mengubah bukti asli.",
    "Jangan menyimpulkan niat pemilik akun hanya dari skor sistem.",
]


def recommend(label: str, level: str = "Sedang", n_accounts: int | None = None,
              coord_label: str | None = None, tni: bool = False) -> dict:
    """Rekomendasi untuk satu unggahan atau satu narasi."""
    base = PLAYBOOK.get(label, PLAYBOOK[C.CAT_NETRAL])
    steps = list(_BASE_STEPS) + list(base["steps"]) if label not in (C.CAT_NETRAL, C.CAT_KLARIFIKASI) else list(base["steps"])
    if coord_label in ("Terkoordinasi kuat", "Indikasi koordinasi", "Spam akun tunggal", "Spam berulang (sedikit akun)"):
        steps += EXTRA_COORDINATED
    if tni:
        steps += EXTRA_INSTITUTION
    return {
        "sla": SLA.get(level, SLA["Sedang"]),
        "unit": base["unit"],
        "steps": steps,
        "template": base["template"],
        "donts": DONTS if label not in (C.CAT_NETRAL, C.CAT_KLARIFIKASI) else [],
        "needs_action": label not in (C.CAT_NETRAL, C.CAT_KLARIFIKASI),
    }


def fill_template(template: str, issue: str = "[ISU]", fact: str = "[FAKTA_RESMI]",
                  source: str = "[SUMBER_RESMI]", channel: str = "[KANAL_RESMI]") -> str:
    """Isi placeholder draf; placeholder yang dikosongkan tetap tampil agar petugas melengkapinya."""
    out = template
    for key, val in (("[ISU]", issue), ("[FAKTA_RESMI]", fact), ("[SUMBER_RESMI]", source), ("[KANAL_RESMI]", channel)):
        if val and val.strip():
            out = out.replace(key, val.strip())
    return out
