"""Profil Akun: indikasi perilaku tidak autentik (bot / jaringan terkoordinasi) per akun alias."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from radar import charts, ui  # noqa: E402
from radar.accounts import FACTOR_WEIGHTS, STRONG, WATCH  # noqa: E402
from radar.report import fmt_int  # noqa: E402

ui.setup()
res = ui.get_result()
posts, accounts = res["posts"], res["accounts"]

ui.hero("Profil Akun", "Indikasi perilaku tidak autentik per akun. Akun dikenali lewat alias; tidak ada upaya mengungkap identitas pemilik.")
ui.note("Skor perilaku hanyalah indikasi untuk memprioritaskan verifikasi manual. Jangan menyimpulkan niat atau identitas pemilik akun hanya dari skor ini.")

if len(accounts) == 0:
    ui.empty_state("Belum ada data akun.")
    st.stop()

counts = accounts["behavior_label"].value_counts()
k1, k2, k3 = st.columns(3)
k1.markdown(ui.kpi("Indikasi kuat tidak autentik", fmt_int(counts.get("Indikasi kuat tidak autentik", 0)), f"skor ≥ {STRONG:.0f}", "#D64545"), unsafe_allow_html=True)
k2.markdown(ui.kpi("Perlu dipantau", fmt_int(counts.get("Perlu dipantau", 0)), f"skor {WATCH:.0f}–{STRONG:.0f}", "#E8B84A"), unsafe_allow_html=True)
k3.markdown(ui.kpi("Normal", fmt_int(counts.get("Normal", 0)), f"dari {fmt_int(len(accounts))} akun", "#2E9E6B"), unsafe_allow_html=True)

st.markdown("")
fig = charts.account_scatter(accounts)
if fig is not None:
    st.plotly_chart(fig, key="accscatter")
    st.caption("Akun baru dengan rasio mengikuti/pengikut sangat tinggi (kanan-bawah ke kiri-atas pada sumbu log) cenderung lebih mencurigakan. Ini hanya salah satu dari enam faktor.")

f1, f2 = st.columns([2, 1])
labels = ["Indikasi kuat tidak autentik", "Perlu dipantau", "Normal"]
sel = f1.multiselect("Tampilkan label", labels, default=labels[:2])
min_posts = f2.number_input("Unggahan minimal", min_value=1, max_value=500, value=1, step=1)
shown = accounts[accounts["behavior_label"].isin(sel) & (accounts["posts"] >= min_posts)].reset_index(drop=True)
st.caption(f"{fmt_int(len(shown))} akun ditampilkan, diurut menurut prioritas tinjauan (0,5 × skor perilaku + 0,5 × risiko konten).")

if len(shown) == 0:
    ui.empty_state("Tidak ada akun yang cocok dengan filter.")
    st.stop()

tab = pd.DataFrame(
    {
        "Akun (alias)": shown["account_id"], "Unggahan": shown["posts"], "Risiko rata-rata": shown["mean_risk"],
        "Skor perilaku": shown["behavior"], "Label": shown["behavior_label"], "Bukti": shown["evidence"],
        "Narasi terkait": shown["narratives"], "Prioritas tinjauan": shown["review_priority"],
    }
)
st.dataframe(
    tab.head(300), hide_index=True,
    column_config={
        "Risiko rata-rata": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Skor perilaku": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Prioritas tinjauan": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
    },
)
if len(shown) > 300:
    st.caption("Menampilkan 300 akun teratas. Gunakan ekspor CSV untuk keseluruhan.")

# ---------------- detail ----------------
st.markdown("### Telaah satu akun")
ids = list(shown["account_id"].head(300))
acc_id = st.selectbox("Pilih akun (alias)", ids)
a = shown[shown["account_id"] == acc_id].iloc[0]
sub = posts[posts["account_id"] == acc_id].sort_values("timestamp")

left, right = st.columns([1, 1], gap="large")
with left:
    names, vals, notes = [], [], []
    for name, w in FACTOR_WEIGHTS.items():
        v = a.get(name)
        names.append(f"{name} (bobot {int(w * 100)}%)")
        if v is None or pd.isna(v):
            vals.append(0.0)
            notes.append("tidak tersedia")
        else:
            vals.append(100 * float(v))
            notes.append(f"{100 * float(v):.0f}")
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color="#8E6BD1", text=notes, textposition="outside"))
    fig.update_xaxes(range=[0, 125], title="Nilai faktor (0–100)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=290, margin=dict(l=10, r=10, t=36, b=10), title=f"Faktor perilaku · skor {a['behavior']:.0f}")
    st.plotly_chart(fig, key="accfactors")
with right:
    st.markdown(f"**Label:** {a['behavior_label']} · **Kecukupan bukti:** {a['evidence']}")
    st.markdown(f"- Unggahan: **{int(a['posts'])}** · berisiko tinggi: **{int(a['high_risk_posts'])}** · narasi terkait: **{int(a['narratives'])}**")
    age = "tidak tersedia" if pd.isna(a["account_age_days"]) else f"{a['account_age_days']:.0f} hari"
    fol = "tidak tersedia" if pd.isna(a["followers"]) else f"{a['followers']:.0f}"
    fing = "tidak tersedia" if pd.isna(a["following"]) else f"{a['following']:.0f}"
    st.markdown(f"- Umur akun: **{age}** · pengikut: **{fol}** · mengikuti: **{fing}**")
    st.markdown(f"- Laju unggah puncak: **{int(a['max_per_hour'])}** unggahan/jam · porsi unggahan bertautan: **{100 * a['url_share']:.0f}%**")
    if a["evidence"] != "Cukup":
        st.warning("Bukti terbatas (kurang dari 5 unggahan): skor kurang dapat diandalkan, verifikasi manual sangat dianjurkan.", icon=":material/info:")

with st.expander(f"Unggahan akun ini ({len(sub)})", icon=":material/list:"):
    v, cfg = ui.posts_view(sub, limit=100)
    st.dataframe(v, column_config=cfg, hide_index=True)

with st.expander("Bagaimana skor perilaku dihitung?", icon=":material/calculate:"):
    st.markdown(
        "Skor 0–100 = rata-rata berbobot dari enam faktor (bobot dinormalisasi ulang bila ada faktor yang datanya tidak tersedia):\n\n"
        + "\n".join(f"- **{k}** ({int(w * 100)}%)" for k, w in FACTOR_WEIGHTS.items())
        + f"\n\nLabel: **Indikasi kuat** ≥ {STRONG:.0f}, **Perlu dipantau** ≥ {WATCH:.0f}, selain itu **Normal**."
    )
