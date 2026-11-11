"""Analisis Teks: skor risiko yang dapat dijelaskan, sorotan isyarat, dan rekomendasi tindakan."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from radar import charts, ui  # noqa: E402
from radar import constants as C  # noqa: E402
from radar.analyzer import analyze_text, highlight_html  # noqa: E402
from radar.playbook import fill_template, recommend  # noqa: E402
from radar.text_utils import mask_pii_keep_length  # noqa: E402

ui.setup()

EXAMPLES = {
    "Hoaks sensasional": "VIRAL!!! Markas satuan menutup posko bantuan banjir, media bungkam! Sebarkan sebelum dihapus!!!",
    "Penipuan rekrutmen": "Lulus tanpa tes! Jalur khusus rekrutmen TNI AD, biaya administrasi transfer ke rekening 0000123456, klik bit.ly/daftarkhusus",
    "Provokasi": "Golongan X biang kerok semua masalah, kita atau mereka! Boikot dan usir dari daerah ini, ayo turun ke jalan malam ini!",
    "Doxxing (data rekaan)": "Ini alamat lengkap dan no hp Pak Fulan 081200001234, NIK 3500000000000123. Ayo geruduk rumahnya, sebarkan data ini!",
    "Klarifikasi resmi": "KLARIFIKASI: Kabar posko bantuan banjir ditutup adalah hoaks. Faktanya posko tetap beroperasi 24 jam. Sumber: rilis resmi satuan.",
    "Kalimat biasa": "Besok ada rapat komunitas pukul 19.00 di balai warga, mohon hadir tepat waktu.",
    "Contoh keterbatasan": "Besok semua sekolah diliburkan, ini info dari teman bapak saya di dinas.",
}
DEFAULT_KEY = "Hoaks sensasional"


def _set_text(text: str) -> None:
    st.session_state["txt_input"] = text


if "txt_input" not in st.session_state:
    st.session_state["txt_input"] = EXAMPLES[DEFAULT_KEY]

ui.hero("Analisis Teks", "Tempel satu unggahan/pesan; sistem menghitung skor risiko dan menjelaskan isyarat penyebabnya.")

st.caption("Coba contoh cepat (seluruhnya fiktif):")
cols = st.columns(len(EXAMPLES))
for col, (label, text) in zip(cols, EXAMPLES.items()):
    col.button(label, key=f"ex_{label}", on_click=_set_text, args=(text,), width="stretch")

text = st.text_area("Teks yang dianalisis", key="txt_input", height=130, max_chars=5000,
                    placeholder="Tempel teks unggahan, pesan berantai, atau komentar di sini…")

if not text or not text.strip():
    ui.empty_state("Masukkan teks untuk dianalisis, atau pilih salah satu contoh cepat di atas.")
    st.stop()

r = analyze_text(text)
level_color = C.LEVEL_COLORS.get(r["level"], "#8A949B")

# ---------------- ringkasan ----------------
c1, c2, c3 = st.columns([1, 1, 1.4], gap="medium")
c1.markdown(ui.kpi("Skor risiko", f"{r['risk']:.0f} / 100", f"Level: {r['level']}", level_color), unsafe_allow_html=True)
c2.markdown(ui.kpi("Kategori dominan", r["label"], "jika risiko ≥ 20", C.CAT_COLORS.get(r["label"], "#8A949B")),
            unsafe_allow_html=True)
rec = recommend(r["label"], r["level"], tni=r["tni_target"])
c3.markdown(ui.kpi("Tenggat tindak lanjut", rec["sla"], f"Unit: {rec['unit']}", "#E8B84A"), unsafe_allow_html=True)

st.markdown("")
st.markdown(f"**Penjelasan:** {r['explanation']}")

if r["pii"]["nik"] or r["pii"]["phone"] or r["pii"]["email"]:
    st.warning(
        f"Terdeteksi data pribadi pada teks (NIK: {r['pii']['nik']}, telepon: {r['pii']['phone']}, email: {r['pii']['email']}). "
        "Aplikasi menyamarkannya pada tampilan, laporan, dan ekspor; jangan menyalin atau menyebarkan ulang.",
        icon=":material/privacy_tip:",
    )

# ---------------- sorotan & skor ----------------
left, right = st.columns([1.5, 1], gap="large")
with left:
    st.markdown("##### Isyarat pada teks")
    shown = mask_pii_keep_length(r["norm"])
    html_text = highlight_html(shown, r["cues"])
    st.markdown(f'<div class="rsd-card rsd-hl">{html_text or "<i>(teks kosong setelah normalisasi)</i>"}</div>', unsafe_allow_html=True)
    legend = " ".join(ui.badge(cat, C.CAT_COLORS[cat]) for cat in C.RISK_CATEGORIES)
    st.markdown(f'<div class="rsd-small" style="margin-top:6px">Warna sorotan: {legend} · abu-abu = isyarat dinegasikan</div>',
                unsafe_allow_html=True)
    st.caption("Teks ditampilkan setelah normalisasi (huruf kecil, slang dibakukan, tautan/akun diganti token) agar pencocokan transparan.")
with right:
    st.plotly_chart(charts.category_scores_fig(r["cat_scores"]), key="catscores")

cues = [c for c in r["cues"]]
if cues:
    with st.expander(f"Rincian {len(cues)} isyarat & aturan yang aktif", icon=":material/rule:"):
        table = pd.DataFrame(
            [
                {"Kategori": c["category"], "Isyarat / aturan": c["cue"], "Bobot dasar": round(c["base_weight"], 2),
                 "Bobot terpakai": round(c["weight"], 2), "Dinegasikan": "ya" if c["negated"] else "tidak"}
                for c in sorted(cues, key=lambda x: -abs(x["weight"]))
            ]
        )
        st.dataframe(table, hide_index=True)
        st.caption("Skor kategori = 1 − e^(−Σbobot/2,2); skor akhir menggabungkan kategori dengan noisy-OR. Kata ber-negasi (mis. “jangan bunuh”) dibobot 15%.")

# ---------------- rekomendasi ----------------
st.markdown("### Rekomendasi tindakan (human-in-the-loop)")
if not rec["needs_action"]:
    st.success(rec["steps"][0] if rec["steps"] else "Tidak perlu tindakan khusus.", icon=":material/check_circle:")
    if r["label"] == C.CAT_KLARIFIKASI:
        for s in rec["steps"][1:]:
            st.markdown(f"- {s}")
else:
    a, b = st.columns([1.2, 1], gap="large")
    with a:
        st.markdown(f"**Langkah yang disarankan** · {ui.level_badge(r['level'])} · {rec['sla']}", unsafe_allow_html=True)
        for i, s in enumerate(rec["steps"], 1):
            st.markdown(f"{i}. {s}")
        if rec["donts"]:
            st.markdown("**Jangan dilakukan:**")
            for s in rec["donts"]:
                st.markdown(f"- {s}")
    with b:
        if rec["template"]:
            st.markdown("**Draf pernyataan (lengkapi lalu tinjau pimpinan)**")
            issue = st.text_input("Isu / topik", key="draft_issue", placeholder="mis. penutupan posko bantuan")
            fact = st.text_input("Fakta resmi", key="draft_fact", placeholder="mis. posko tetap beroperasi 24 jam")
            source = st.text_input("Sumber resmi", key="draft_source", placeholder="mis. rilis resmi tanggal …")
            channel = st.text_input("Kanal resmi", key="draft_channel", placeholder="mis. akun resmi satuan")
            st.code(fill_template(rec["template"], issue, fact, source, channel), language="text", wrap_lines=True)
            st.caption("Placeholder dalam [KURUNG] harus dilengkapi petugas. Sistem tidak menerbitkan apa pun secara otomatis.")

ui.note("Skor adalah indikasi untuk memprioritaskan tinjauan manusia, bukan putusan benar/salah. "
        "Pendekatan berbasis kamus dapat melewatkan kalimat tanpa isyarat eksplisit (lihat halaman Validasi).")
