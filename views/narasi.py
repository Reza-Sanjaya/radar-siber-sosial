"""Narasi & Koordinasi: kelompok unggahan serupa, skor koordinasi, dan linimasa penyebaran."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from radar import charts, ui  # noqa: E402
from radar import constants as C  # noqa: E402
from radar.coordination import coordination_components  # noqa: E402
from radar.playbook import fill_template, recommend  # noqa: E402
from radar.report import fmt_int, relevant_narratives  # noqa: E402

ui.setup()
res = ui.get_result()
meta, posts, narr, accounts = res["meta"], res["posts"], res["narratives"], res["accounts"]

ui.hero("Narasi & Koordinasi", "Unggahan yang bermakna sama dikelompokkan menjadi narasi, lalu diuji apakah penyebarannya tampak terkoordinasi.")

if len(narr) == 0:
    ui.empty_state("Tidak ada narasi yang terbentuk. Coba turunkan ambang kemiripan atau ukuran narasi minimal di menu Data & Laporan.")
    st.stop()

# ---------------- filter ----------------
f1, f2 = st.columns([1, 2])
only_rel = f1.toggle("Hanya narasi berisiko / terindikasi koordinasi", value=True,
                     help="Narasi dengan rata-rata risiko ≥ 25 atau skor koordinasi ≥ 45. Matikan untuk melihat semua narasi, termasuk percakapan wajar.")
cats = sorted(narr["top_label"].unique())
sel_cats = f2.multiselect("Kategori dominan", cats, default=[], placeholder="Semua kategori")

view_df = relevant_narratives(narr) if only_rel else narr
if sel_cats:
    view_df = view_df[view_df["top_label"].isin(sel_cats)]
view_df = view_df.sort_values("priority", ascending=False).reset_index(drop=True)

st.caption(f"Menampilkan {len(view_df)} dari {len(narr)} narasi · ambang kemiripan {meta['sim_threshold']:.2f} · ukuran minimal {meta['min_cluster']} unggahan")
if len(view_df) == 0:
    ui.empty_state("Tidak ada narasi yang cocok dengan filter. Ubah filter di atas.")
    st.stop()

table = pd.DataFrame(
    {
        "ID": view_df["narrative"], "Kategori": view_df["top_label"], "Unggahan": view_df["size"], "Akun": view_df["n_accounts"],
        "Risiko rata-rata": view_df["mean_risk"], "Skor koordinasi": view_df["coordination"], "Label koordinasi": view_df["coord_label"],
        "Prioritas": view_df["priority"], "Pertama terlihat": view_df["first_seen"], "Tagar": view_df["hashtags"],
    }
)
st.dataframe(
    table, hide_index=True,
    column_config={
        "Risiko rata-rata": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Skor koordinasi": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Prioritas": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Pertama terlihat": st.column_config.DatetimeColumn(format="DD MMM HH:mm"),
    },
)

# ---------------- detail ----------------
st.markdown("### Telaah satu narasi")
options = list(view_df["narrative"])
labels = {
    r["narrative"]: f"{r['narrative']} · {r['top_label']} · {int(r['size'])} unggahan · koordinasi {r['coordination']:.0f}"
    for _, r in view_df.iterrows()
}
chosen = st.selectbox("Pilih narasi", options, format_func=lambda k: labels.get(k, k))
n = view_df[view_df["narrative"] == chosen].iloc[0]
sub = posts[posts["narrative"] == chosen]

coord_color = "#D64545" if n["coordination"] >= C.COORD_STRONG else ("#E8782B" if n["coordination"] >= C.COORD_INDICATION else "#2E9E6B")
k1, k2, k3, k4 = st.columns(4)
k1.markdown(ui.kpi("Unggahan / akun", f"{int(n['size'])} / {int(n['n_accounts'])}", f"{n['posts_per_hour']:.1f} unggahan per jam".replace(".", ","), "#3C9BD1"), unsafe_allow_html=True)
k2.markdown(ui.kpi("Rentang waktu", f"{n['span_hours']:.1f} jam".replace(".", ","), f"puncak {int(n['peak_hour_posts'])} unggahan/jam", "#8E6BD1"), unsafe_allow_html=True)
k3.markdown(ui.kpi("Skor koordinasi", f"{n['coordination']:.0f}", str(n["coord_label"]), coord_color), unsafe_allow_html=True)
k4.markdown(ui.kpi("Risiko rata-rata", f"{n['mean_risk']:.0f}", f"kategori: {n['top_label']}", C.LEVEL_COLORS.get(C.risk_level(n["mean_risk"]), "#888")), unsafe_allow_html=True)

st.markdown("")
a, b = st.columns([1.35, 1], gap="large")
with a:
    fig = charts.narrative_timeline(sub)
    if fig is not None:
        st.plotly_chart(fig, key="ntimeline")
        st.caption("Setiap titik = satu unggahan; sumbu-y = akun (urut kemunculan pertama). Titik yang menumpuk rapat dalam waktu singkat dari banyak akun adalah ciri khas amplifikasi terkoordinasi.")
with b:
    _, comp = coordination_components(int(n["size"]), int(n["n_accounts"]), int(n["peak_hour_posts"]), float(n["tightness"]),
                                      None if pd.isna(n["new_account_share"]) else float(n["new_account_share"]), float(n["overlap_share"]))
    fig = charts.components_fig(comp)
    if fig is not None:
        st.plotly_chart(fig, key="ncomp")
    flagged = 0
    if len(accounts):
        ids = set(sub["account_id"])
        flagged = int(((accounts["behavior_label"] == "Indikasi kuat tidak autentik") & accounts["account_id"].isin(ids)).sum())
    st.markdown(f"**Akun terindikasi tidak autentik pada narasi ini:** {flagged} dari {int(n['n_accounts'])} akun")
    st.markdown(f"**Akun pertama (alias):** `{n['origin_account']}` pada {pd.Timestamp(n['origin_time']):%d %b %H:%M}")
    if n["hashtags"]:
        st.markdown(f"**Tagar khas:** {n['hashtags']}")
    with st.expander("Arti label koordinasi"):
        st.markdown(
            "- **Terkoordinasi kuat** (skor ≥ 70): lonjakan sangat padat dalam waktu singkat dari banyak akun dengan teks mirip.\n"
            "- **Indikasi koordinasi** (45–69): ada pola serentak, perlu verifikasi manual.\n"
            "- **Spam berulang (sedikit akun)**: teks nyaris sama diunggah berulang oleh beberapa akun yang sama.\n"
            "- **Spam akun tunggal**: satu akun mengulang pesan yang sama.\n"
            "- **Tidak terindikasi koordinasi**: penyebaran tidak menunjukkan pola serentak. Ini BUKAN bukti bahwa narasi tersebut benar atau aman."
        )

st.markdown("**Contoh teks narasi (tersamarkan):**")
st.code(str(n["sample_text"]), language="text", wrap_lines=True)

# ---------------- rekomendasi ----------------
rec = recommend(n["top_label"], C.risk_level(n["mean_risk"]), int(n["n_accounts"]), n["coord_label"], bool(n["tni_share"] >= 0.5))
if rec["needs_action"]:
    st.markdown("### Rekomendasi tindakan")
    x, y = st.columns([1.2, 1], gap="large")
    with x:
        st.markdown(f"{ui.level_badge(C.risk_level(n['mean_risk']))} {rec['sla']} · unit: {rec['unit']}", unsafe_allow_html=True)
        for i, s in enumerate(rec["steps"], 1):
            st.markdown(f"{i}. {s}")
        for s in rec["donts"]:
            st.markdown(f"- :red[Jangan] {s[0].lower() + s[1:]}")
    with y:
        if rec["template"]:
            st.markdown("**Draf pernyataan**")
            issue = st.text_input("Isu / topik", key="n_issue", placeholder="mis. penutupan posko bantuan")
            fact = st.text_input("Fakta resmi", key="n_fact")
            source = st.text_input("Sumber resmi", key="n_source")
            channel = st.text_input("Kanal resmi", key="n_channel")
            st.code(fill_template(rec["template"], issue, fact, source, channel), language="text", wrap_lines=True)
else:
    st.success("Narasi ini tidak memerlukan tindakan khusus; cukup dipantau.", icon=":material/check_circle:")

with st.expander(f"Seluruh unggahan dalam {chosen} ({fmt_int(len(sub))})", icon=":material/list:"):
    v, cfg = ui.posts_view(sub.sort_values("timestamp"), limit=200)
    st.dataframe(v, column_config=cfg, hide_index=True)
    if len(sub) > 200:
        st.caption("Menampilkan 200 unggahan pertama. Gunakan ekspor CSV di menu Data & Laporan untuk keseluruhan.")
