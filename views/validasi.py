"""Validasi: uji kewajaran mesin analisis pada himpunan uji berlabel, lengkap dengan kesalahan dan keterbatasannya."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from radar import charts, ui  # noqa: E402
from radar import constants as C  # noqa: E402
from radar.evaluation import evaluate  # noqa: E402

ui.setup()
ui.hero("Validasi & Keterbatasan", "Seberapa baik mesin analisis bekerja, dan di mana ia salah. Ditampilkan apa adanya.")

ui.note("Kejujuran metodologi: himpunan uji ditulis oleh pengembang yang sama dengan pembuat kamus isyarat, dan beberapa kesalahan "
        "dipakai untuk memperbaiki kamus. Angka di bawah adalah uji kewajaran (sanity check), BUKAN klaim akurasi di dunia nyata.")

thr = st.slider("Ambang skor untuk dianggap 'berisiko'", 20, 70, int(C.BINARY_RISK_THRESHOLD), 5,
                help="Unggahan berskor ≥ ambang dianggap terdeteksi berisiko. Geser untuk melihat pertukaran presisi–recall.")
ev = evaluate(float(thr))


def pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


o = ev["overall"]
c1, c2, c3, c4 = st.columns(4)
c1.markdown(ui.kpi("Presisi", pct(o["precision"]), f"{ev['tp']} benar dari {ev['tp'] + ev['fp']} ditandai", "#3C9BD1"), unsafe_allow_html=True)
c2.markdown(ui.kpi("Recall", pct(o["recall"]), f"{ev['tp']} dari {ev['tp'] + ev['fn']} yang berisiko", "#2E9E6B"), unsafe_allow_html=True)
c3.markdown(ui.kpi("F1", pct(o["f1"]), "rata-rata harmonik", "#E8B84A"), unsafe_allow_html=True)
c4.markdown(ui.kpi("Akurasi kategori", pct(ev["category_accuracy"]), "kategori benar pada yang terdeteksi", "#8E6BD1"), unsafe_allow_html=True)

st.markdown("")
a, b = st.columns([1.3, 1], gap="large")
with a:
    fig = charts.evaluation_fig(ev["per_category"])
    if fig is not None:
        st.plotly_chart(fig, key="evalcat")
with b:
    st.markdown("##### Mudah vs sulit")
    rows = []
    for diff, v in ev["by_difficulty"].items():
        rows.append({"Tingkat": diff.capitalize(), "Jumlah": v["n"], "Presisi": pct(v["precision"]), "Recall": pct(v["recall"]),
                     "Terlewat": v["fn"], "Salah tandai": v["fp"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.markdown(
        "**Mudah** = kalimat memuat isyarat kata yang jelas. **Sulit** = tanpa isyarat eksplisit (kabar tanpa kata kunci, ancaman "
        "tersirat, rekayasa sosial halus) atau kalimat wajar yang mirip pola berisiko."
    )

st.markdown(
    f"Himpunan uji: **{ev['n']} kalimat** ({ev['tp'] + ev['fn']} berisiko, {ev['tn'] + ev['fp']} tidak berisiko, termasuk kalimat wajar yang "
    "sengaja dibuat mirip pola berisiko, mis. “rapat pukul 19.00”, “serangan jantung”, “sate bakar”)."
)

st.markdown("### Kesalahan yang terjadi")
errs = ev["errors"]
if len(errs) == 0:
    st.success("Tidak ada kesalahan pada ambang ini.", icon=":material/check_circle:")
else:
    errs = errs.rename(columns={"id": "ID", "jenis": "Jenis", "kesulitan": "Tingkat", "label": "Label benar",
                                "pred_label": "Prediksi", "risk": "Skor", "text": "Teks"})
    st.dataframe(errs, hide_index=True, column_config={"Teks": st.column_config.TextColumn(width="large")})
    st.caption("Kesalahan ini sengaja ditampilkan: mereka menunjukkan batas pendekatan berbasis kamus dan menjadi dasar peta jalan peningkatan.")

st.markdown("### Keterbatasan yang diketahui")
st.markdown(
    "- **Berbasis kamus:** kuat pada isyarat eksplisit, lemah pada kalimat tanpa kata kunci, sarkasme, ironi, dan bahasa daerah.\n"
    "- **Tidak memverifikasi kebenaran fakta:** sistem menilai *ciri* konten berisiko, bukan benar/salahnya klaim. Verifikasi tetap oleh manusia.\n"
    "- **Koordinasi ≠ pasti kampanye:** tren organik dan aksi spontan yang serentak dapat tampak mirip; karena itu ada label bertingkat dan penahan klarifikasi.\n"
    "- **Data demo sintetis:** hasil pada data nyata dapat berbeda dan perlu kalibrasi oleh satuan pengguna.\n"
    "- **Tidak ada aksi otomatis:** seluruh rekomendasi bersifat saran bagi petugas (human-in-the-loop)."
)
st.markdown("### Rencana peningkatan")
st.markdown(
    "1. Tambahkan model semantik (embedding / klasifikasi berbahasa Indonesia) sebagai *lapisan kedua* di atas kamus, dan bandingkan pada himpunan uji independen.\n"
    "2. Susun himpunan uji berlabel oleh beberapa penelaah (inter-annotator agreement) agar angka evaluasi lebih objektif.\n"
    "3. Kalibrasi ambang dengan umpan balik analis (tombol “benar/salah”) pada pemakaian nyata.\n"
    "4. Perluas kamus dengan istilah daerah dan tren baru melalui proses tinjauan berkala."
)
