"""Tentang & Kepatuhan: masalah, solusi, cara kerja, inovasi, kelayakan, dan pemetaan ke rulebook & kriteria penilaian."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from radar import __version__  # noqa: E402
from radar import constants as C  # noqa: E402
from radar import ui  # noqa: E402
from radar.accounts import FACTOR_WEIGHTS  # noqa: E402
from radar.early_warning import ISS_WEIGHTS  # noqa: E402
from radar.lexicon import lexicon_summary  # noqa: E402

ui.setup()
ui.hero("Tentang & Kepatuhan", f"{C.APP_NAME} v{__version__} · Kartika Cyber Hackathon 2026 · Kategori Siber Sosial")

t1, t2, t3, t4, t5 = st.tabs(["Ringkasan", "Cara kerja", "Inovasi & kelayakan", "Kepatuhan rulebook", "Teknologi & atribusi"])

# =========================================================================== #
with t1:
    st.markdown("### Masalah")
    st.markdown(
        "Ancaman terhadap satuan tidak selalu berupa serangan teknis. Hoaks tentang satuan atau bantuan kemanusiaan, provokasi yang "
        "memecah belah, penipuan yang **mencatut nama institusi** (mis. rekrutmen palsu), dan pembocoran data pribadi dapat merusak "
        "kepercayaan publik dan memicu gangguan keamanan, sering kali **disebarkan serentak oleh jaringan akun**. "
        "Pemantauan manual lambat, tidak konsisten, dan sulit membedakan *tren organik* dari *kampanye terkoordinasi*."
    )
    st.markdown("### Solusi")
    st.markdown(
        f"**{C.APP_NAME}** adalah dasbor deteksi dini untuk ruang siber sosial. Ia mengubah tumpukan unggahan menjadi "
        "**satu indeks yang mudah dibaca (ISS)**, daftar **peringatan beralasan**, dan **rekomendasi tindakan** yang tetap berada di tangan petugas."
    )
    cols = st.columns(3)
    feats = [
        ("Skor risiko yang dapat dijelaskan", "Lima kategori ancaman, penanganan negasi, penahan klarifikasi/cek fakta, dan sorotan isyarat per kata."),
        ("Deteksi narasi & koordinasi", "Pengelompokan unggahan serupa, linimasa penyebaran, dan Skor Koordinasi dari lima sinyal transparan."),
        ("Profil akun tidak autentik", "Enam faktor perilaku (laju unggah, konten kembar, umur akun, rasio mengikuti, dll.) dengan alias akun."),
        ("Indeks Siber Sosial (ISS)", "Status AMAN / WASPADA / SIAGA / AWAS beserta komponen penyusunnya, plus replay waktu."),
        ("Rekomendasi & draf klarifikasi", "Langkah tindak lanjut per kategori, tenggat (SLA), larangan, dan draf pernyataan siap lengkapi."),
        ("Laporan SITREP otomatis", "Satu berkas HTML siap cetak dengan ringkasan eksekutif, narasi prioritas, dan hash keutuhan data."),
    ]
    for i, (t, d) in enumerate(feats):
        with cols[i % 3]:
            st.markdown(f'<div class="rsd-card" style="margin-bottom:10px"><b>{ui.esc(t)}</b><br><span class="rsd-small">{ui.esc(d)}</span></div>',
                        unsafe_allow_html=True)
    st.markdown("### Alur demo 3 menit untuk Dewan Juri")
    st.markdown(
        "1. **Pusat Komando:** lihat ISS berstatus AWAS, peringatan beralasan, lalu geser *replay* untuk melihat bagaimana peringatan muncul.\n"
        "2. **Narasi & Koordinasi:** buka narasi hoaks posko; amati linimasa yang menumpuk serentak dari akun-akun baru. "
        "Bandingkan dengan topik organik (bola/diskon) yang *tidak* ditandai.\n"
        "3. **Analisis Teks:** coba contoh cepat atau ketik kalimat sendiri; lihat sorotan isyarat dan draf klarifikasi.\n"
        "4. **Data & Laporan:** unggah CSV sendiri (atau pakai demo) lalu unduh laporan SITREP.\n"
        "5. **Validasi:** lihat angka kinerja *beserta kesalahannya*."
    )
    ui.note("Karya ini bukan produk resmi TNI AD/PUSSIBERAD dan tidak memakai logo atau identitas resmi pihak mana pun. "
            "Seluruh data demo adalah rekaan.")

# =========================================================================== #
with t2:
    st.markdown("### Arsitektur (berjalan offline, tanpa API pihak ketiga)")
    ui.flow([
        ("1. Masukan", "CSV/XLSX unggahan (atau data demo). Validasi kolom, parsing waktu, anonimisasi akun."),
        ("2. Normalisasi", "Huruf kecil, slang dibakukan, huruf berulang diringkas, tautan/akun diganti token."),
        ("3. Skor konten", "Kamus isyarat 5 kategori + aturan ko-okurensi + negasi + klarifikasi, digabung noisy-OR."),
        ("4. Narasi & koordinasi", "Kemiripan Jaccard + union-find, lalu Skor Koordinasi per narasi."),
        ("5. Akun & anomali", "Skor perilaku akun; deteksi lonjakan (EWMA + z-score)."),
        ("6. ISS & peringatan", "Indeks 0–100, peringatan berbasis aturan, rekomendasi, SITREP."),
    ])
    st.markdown("### Komponen ISS")
    st.dataframe(pd.DataFrame({"Komponen": list(ISS_WEIGHTS.keys()), "Bobot": [f"{int(w * 100)}%" for w in ISS_WEIGHTS.values()]}), hide_index=True)
    st.caption("ISS = 100 × Σ (bobot × nilai komponen, 0–1) pada jendela 24 jam terakhir. Status: AMAN < 25 ≤ WASPADA < 50 ≤ SIAGA < 75 ≤ AWAS.")

    st.markdown("### Skor Koordinasi narasi")
    st.latex(r"K = 100 \times \text{kepadatan waktu} \times (0{,}5 + 0{,}5 \times \text{pendukung}) \times \text{keyakinan ukuran}")
    st.markdown(
        "- **Kepadatan waktu:** porsi unggahan yang jatuh pada jendela 60 menit terpadat.\n"
        "- **Pendukung:** 40% keragaman akun + 30% kemiripan teks + 20% porsi akun baru + 10% akun lintas-narasi.\n"
        "- **Keyakinan ukuran:** min(1, √(ukuran/8)) agar narasi kecil tidak dinilai berlebihan.\n"
        "- Keragaman akun **tidak berdiri sendiri**: banyak akun yang menulis hal serupa pada waktu berbeda (tren organik) tidak dianggap terkoordinasi."
    )
    st.markdown("### Faktor perilaku akun")
    st.dataframe(pd.DataFrame({"Faktor": list(FACTOR_WEIGHTS.keys()), "Bobot": [f"{int(w * 100)}%" for w in FACTOR_WEIGHTS.values()]}), hide_index=True)

    st.markdown("### Kamus isyarat (transparan & dapat diaudit)")
    summ = lexicon_summary()
    st.dataframe(pd.DataFrame({"Kelompok": list(summ.keys()), "Jumlah isyarat": list(summ.values())}), hide_index=True)
    st.caption("Setiap isyarat berbobot dan dapat dilihat pada halaman Analisis Teks. Tidak ada model kotak-hitam: setiap skor dapat ditelusuri ke kata penyebabnya.")

# =========================================================================== #
with t3:
    st.markdown("### Yang membedakan")
    st.markdown(
        "- **Menjawab pertanyaan operasional, bukan sekadar klasifikasi:** “Apakah ini kampanye terkoordinasi? Seberapa mendesak? Apa langkah pertama?”\n"
        "- **Membedakan tren organik dari kampanye** (kontrol bola/diskon pada data demo) sehingga tidak banjir peringatan palsu.\n"
        "- **Penahan false positive:** konten klarifikasi/cek fakta dan kalimat bernegasi (“jangan bunuh”) diturunkan skornya.\n"
        "- **Indeks tunggal ISS + replay waktu:** pimpinan melihat status dalam sekali pandang; analis menelusuri sebab-sebabnya.\n"
        "- **Privasi sejak desain:** alias akun, penyamaran data pribadi, tanpa penyimpanan, tanpa pengiriman data keluar.\n"
        "- **Jujur soal batas:** halaman Validasi menampilkan kesalahan, bukan hanya angka terbaik."
    )
    st.markdown("### Kelayakan implementasi di satuan")
    st.markdown(
        "- **Ringan & offline:** hanya Python + beberapa pustaka umum; tanpa GPU, tanpa internet, dan tanpa API berbayar, sehingga cocok untuk jaringan tertutup.\n"
        "- **Masukan sederhana:** CSV/XLSX dari alat pemantauan yang sudah dimiliki satuan; format kolom fleksibel.\n"
        "- **Cepat:** ±1.400 unggahan dianalisis sekitar 1 detik; batas 20.000 unggahan per analisis.\n"
        "- **Human-in-the-loop:** tidak ada tindakan otomatis; rekomendasi disesuaikan dengan SOP dan kewenangan satuan.\n"
        "- **Mudah diaudit & dirawat:** kamus dan bobot berupa berkas teks yang dapat disunting tanpa melatih ulang model."
    )
    st.markdown("### Peta jalan pengembangan lanjutan")
    st.dataframe(
        pd.DataFrame(
            [
                ("Jangka pendek", "Konektor ekspor dari alat pemantauan yang ada; mode kumpulan harian terjadwal; umpan balik analis (benar/salah)."),
                ("Jangka menengah", "Lapisan model semantik bahasa Indonesia di atas kamus; himpunan uji beranotasi banyak penelaah; peta jaringan akun."),
                ("Jangka panjang", "Integrasi dengan sistem pelaporan satuan, peringatan multi-wilayah, dan dasbor lintas satuan."),
            ],
            columns=["Tahap", "Rencana"],
        ),
        hide_index=True,
    )

# =========================================================================== #
with t4:
    st.markdown("### Pemetaan ke kriteria penilaian")
    st.dataframe(
        pd.DataFrame(
            [
                ("Relevansi & manfaat (25%)", "Menangani ancaman non-teknis yang menyasar institusi: hoaks, provokasi, penipuan rekrutmen yang mencatut nama institusi, doxxing; prioritas dinaikkan bila konten menyebut satuan/institusi."),
                ("Inovasi teknis (25%)", "Skor koordinasi lima sinyal, pembeda tren organik vs kampanye, ISS + replay, penahan false positive, semua dapat dijelaskan dan offline."),
                ("Fungsionalitas purwarupa (25%)", "Aplikasi berjalan penuh: data demo, unggah data sendiri, 7 halaman, ekspor laporan/CSV, pengujian otomatis."),
                ("Kelayakan implementasi (15%)", "Ringan, offline, masukan CSV, human-in-the-loop, peta jalan bertahap."),
                ("Kualitas dokumentasi (10%)", "README, naskah video, slide, panduan deploy, metodologi & keterbatasan, halaman Validasi."),
            ],
            columns=["Kriteria", "Bukti pada karya"],
        ),
        hide_index=True,
    )
    st.markdown("### Kepatuhan terhadap ketentuan karya")
    st.dataframe(
        pd.DataFrame(
            [
                ("Kategori dipilih: Siber Sosial", "Memantau & menganalisis ruang siber sosial untuk mendeteksi ancaman non-teknis (disinformasi, provokasi, penipuan, doxxing)."),
                ("Karya asli selama periode program", "Dikembangkan pada periode program (November 2026). Tidak ada karya pre-existing sebagai dasar pengembangan."),
                ("Pustaka/alat pihak ketiga dengan atribusi", "Streamlit, pandas, NumPy, Plotly, openpyxl: seluruhnya sumber terbuka; lihat tab Teknologi & atribusi."),
                ("Tanpa malware aktif", "Aplikasi hanya membaca & menganalisis teks; tidak menjalankan kode dari data, tidak membuka tautan, tidak melakukan pemindaian jaringan."),
                ("Tanpa konten SARA/pornografi/ujaran kebencian", "Aplikasi bertujuan MENDETEKSI konten semacam itu. Contoh pada data demo adalah rekaan generik untuk uji deteksi dan tidak menyasar kelompok nyata."),
                ("Tanpa data pribadi pihak ketiga tanpa izin", "Data demo 100% sintetis (akun alias, nomor & NIK rekaan tak valid). Data unggahan dialiaskan dan data pribadi disamarkan; tidak ada scraping."),
                ("Tidak melanggar hak kekayaan intelektual", "Tidak memakai logo, aset, atau data milik pihak lain. Kode ditulis untuk karya ini; pustaka OSS diatribusi."),
                ("Satu submission", "Pembaruan dilakukan pada karya yang sama sebelum batas akhir 15 November 2026 pukul 23.59 WIB."),
                ("Kode etik: tidak menyerang pihak lain", "Tidak ada fitur ofensif; rekomendasi secara eksplisit melarang doxxing balasan, serangan siber, dan penghapusan bukti."),
            ],
            columns=["Ketentuan", "Pemenuhan"],
        ),
        hide_index=True,
    )
    st.markdown("### Kelengkapan submission")
    st.dataframe(
        pd.DataFrame(
            [
                ("Link karya/project", "Tautan publik yang dapat dicoba juri (mis. Streamlit Community Cloud)", "docs/03_panduan_deploy.md"),
                ("Thumbnail", "1200×630 px, JPG/PNG/WebP, maks 500 KB", "submission/thumbnail.jpg"),
                ("Screenshot", "Maks 5 gambar antarmuka", "submission/screenshot_1..5.png"),
                ("Video karya", "Maks 10 menit, diunggah ke YouTube", "docs/02_naskah_video.md (naskah)"),
                ("Slide penjelasan", "Fitur, arsitektur, teknologi, dan informasi umum", "submission/slide_penjelasan.pptx"),
            ],
            columns=["Item", "Ketentuan", "Lokasi pada folder proyek"],
        ),
        hide_index=True,
    )

# =========================================================================== #
with t5:
    st.markdown("### Pustaka pihak ketiga (open source) dan atribusi")
    st.dataframe(
        pd.DataFrame(
            [
                ("Streamlit", "Apache-2.0", "Kerangka antarmuka web"),
                ("pandas", "BSD-3-Clause", "Pengolahan data tabular"),
                ("NumPy", "BSD-3-Clause", "Komputasi numerik"),
                ("Plotly (plotly.py)", "MIT", "Grafik interaktif"),
                ("openpyxl", "MIT", "Membaca berkas XLSX"),
            ],
            columns=["Pustaka", "Lisensi", "Fungsi"],
        ),
        hide_index=True,
    )
    st.markdown("### Pernyataan pengembangan")
    st.markdown(
        "- Mesin analisis (kamus isyarat, skor, koordinasi, ISS) dan antarmuka dibuat khusus untuk karya ini; **tidak ada model AI pihak ketiga yang dipanggil saat aplikasi berjalan**.\n"
        "- Pengembangan kode dibantu asisten AI (Claude, Anthropic) di bawah arahan peserta; seluruh keluaran ditinjau, diuji, dan dapat dijelaskan oleh peserta.\n"
        "- Data demo dibangkitkan oleh generator sintetis di `radar/synth.py` (seed tetap, dapat direproduksi)."
    )
    st.caption("Versi aplikasi: " + __version__)
