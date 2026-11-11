"""Radar Siber Sosial - deteksi dini ancaman non-teknis di ruang siber sosial.

Paket ini berisi mesin analisis (tanpa model eksternal, berjalan offline):
    text_utils   -> normalisasi teks Indonesia, fitur permukaan, masking data pribadi
    lexicon      -> kamus isyarat (cue) yang transparan dan dapat diaudit
    analyzer     -> skor risiko konten yang dapat dijelaskan
    coordination -> pengelompokan narasi & deteksi perilaku terkoordinasi
    accounts     -> skor perilaku tidak autentik per akun
    early_warning-> deteksi anomali & Indeks Siber Sosial (ISS)
    playbook     -> rekomendasi tindakan & draf klarifikasi (human-in-the-loop)
    data         -> pemuatan CSV, validasi, anonimisasi
    synth        -> generator data sintetis (fiktif)
    pipeline     -> orkestrasi seluruh analisis
    report       -> laporan HTML / CSV
"""

__version__ = "1.0.0"
