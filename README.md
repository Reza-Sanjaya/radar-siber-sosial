# Radar Siber Sosial

**Deteksi dini ancaman non-teknis di ruang siber sosial.**
Karya untuk **Kartika Cyber Hackathon 2026**, kategori **Siber Sosial**.

Radar Siber Sosial mengubah tumpukan unggahan media sosial menjadi satu indeks yang mudah dibaca (**Indeks Siber Sosial / ISS**), daftar **peringatan beralasan**, dan **rekomendasi tindakan**. Keputusan akhir tetap di tangan petugas (*human-in-the-loop*).

| Fitur | Isi |
|---|---|
| Skor risiko yang dapat dijelaskan | 5 kategori: disinformasi, provokasi, kebencian/kekerasan, penipuan/phishing, doxxing. Ada penanganan negasi dan penahan klarifikasi/cek fakta. Isyarat disorot per kata. |
| Narasi & koordinasi | Unggahan serupa dikelompokkan, lalu diuji dengan Skor Koordinasi (5 sinyal). Tren organik tidak salah ditandai sebagai kampanye. |
| Profil akun | 6 faktor perilaku akun tidak autentik; akun dialiaskan. |
| ISS + replay waktu | Status AMAN / WASPADA / SIAGA / AWAS, komponen transparan, bisa diputar ulang. |
| Rekomendasi & draf klarifikasi | Langkah, tenggat, larangan, dan draf pernyataan. |
| Laporan SITREP | HTML siap cetak + CSV (aman dari injeksi formula). |
| Validasi jujur | Halaman khusus yang menampilkan metrik **beserta kesalahannya**. |

Berjalan **sepenuhnya offline** (tanpa API/model pihak ketiga saat aplikasi berjalan). Data demo **100% sintetis**.

## Menjalankan di Windows (paling mudah)

1. Pasang Python 3.11+ dari python.org (centang **Add python.exe to PATH**).
2. Ekstrak folder ini, lalu klik dua kali **`jalankan_windows.bat`**.
3. Peramban terbuka otomatis di `http://localhost:8501`.

Cara manual:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Alur demo 3 menit
1. **Pusat Komando**: ISS berstatus AWAS; geser *replay* untuk melihat kapan peringatan muncul.
2. **Narasi & Koordinasi**: buka N-01 (hoaks posko); lihat linimasa yang menumpuk serentak dari akun baru. Bandingkan dengan topik organik (bola/diskon) yang tidak ditandai.
3. **Analisis Teks**: klik contoh cepat atau ketik sendiri.
4. **Data & Laporan**: unggah CSV sendiri (template tersedia), unduh SITREP.
5. **Validasi**: lihat metrik dan kesalahannya.

## Format data unggahan
CSV/XLSX dengan kolom wajib `timestamp`, `account_id`, `text`. Opsional: `platform, likes, shares, replies, followers, following, account_age_days, post_id`. Nama kolom Indonesia/Inggris umum dikenali otomatis. Batas 20.000 baris.

## Struktur folder
```
app.py                 titik masuk Streamlit
radar/                 mesin analisis (text_utils, lexicon, analyzer, coordination, accounts, early_warning, playbook, report, ...)
views/                 7 halaman aplikasi
data/                  sample_posts.csv (sintetis), eval_set.csv (himpunan uji)
tests/                 100 tes otomatis (pytest)
tools/generate_sample.py  membangkitkan ulang data sintetis
docs/                  naskah video, panduan deploy, checklist submission, deskripsi karya
submission/            thumbnail, screenshot, slide
```

## Pengujian
```
pip install -r requirements-dev.txt
python -m pytest tests -q
```
Mencakup mesin analisis, pemuatan data (format waktu, encoding, kolom), kasus tepi pipeline (1 baris, teks aneh, injeksi HTML/formula), dan seluruh halaman UI. Lulus pada Python 3.13 dengan pandas 3 maupun pandas 2.x.

## Kepatuhan terhadap rulebook (ringkas)
- Data demo sintetis; akun alias; nomor/NIK rekaan tak valid; **tanpa scraping**; data unggahan dialiaskan dan data pribadi disamarkan.
- Contoh konten provokatif memakai kelompok **fiktif ("Golongan X")**, tanpa identitas SARA nyata, agar karya sendiri tidak memuat ujaran kebencian. Kamus deteksi di kode lebih luas daripada data contoh.
- Tidak ada fitur ofensif; tanpa malware; tanpa logo/aset pihak lain. Bukan produk resmi TNI AD/PUSSIBERAD.
- Pemetaan lengkap ada di halaman **Tentang & Kepatuhan**.

## Keterbatasan (apa adanya)
Pendekatan berbasis kamus kuat pada isyarat eksplisit, lemah pada kalimat tanpa kata kunci, sarkasme, dan bahasa daerah. Sistem menilai *ciri* konten, bukan kebenaran klaim. Himpunan uji (105 kalimat) ditulis oleh pengembang yang sama dengan pembuat kamus, jadi angkanya (presisi 100%, recall ±85%, di mana semua kalimat "sulit" terlewat) adalah uji kewajaran, **bukan** klaim akurasi dunia nyata.

## Atribusi
Streamlit (Apache-2.0), pandas (BSD-3), NumPy (BSD-3), Plotly (MIT), openpyxl (MIT). Pengembangan kode dibantu asisten AI (Claude, Anthropic) di bawah arahan peserta; tidak ada model AI yang dipanggil saat aplikasi berjalan. Hak kekayaan intelektual karya tetap milik peserta.
