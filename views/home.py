"""Pusat Komando: Indeks Siber Sosial, peringatan dini, tren, dan prioritas tindak."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from radar import charts, ui  # noqa: E402
from radar import constants as C  # noqa: E402
from radar.early_warning import build_alerts, compute_iss  # noqa: E402
from radar.report import executive_summary, fmt_int, relevant_narratives  # noqa: E402

ui.setup()
res = ui.get_result()
ds = ui.dataset()
meta, posts, narr, accounts, series = res["meta"], res["posts"], res["narratives"], res["accounts"], res["series"]

ui.hero("Pusat Komando Siber Sosial", "Deteksi dini disinformasi, provokasi, penipuan, dan kebocoran data di ruang siber sosial.")

if ds["source"] == "demo":
    ui.note("Anda melihat DATA DEMO SINTETIS (100% fiktif: akun, nomor, dan peristiwa rekaan). "
            "Untuk menganalisis data sendiri, buka menu Data & Laporan.")
for w in ds.get("warnings", []):
    st.warning(w, icon=":material/warning:")

if meta["n_posts"] == 0:
    ui.empty_state("Belum ada data untuk dianalisis. Buka menu Data & Laporan untuk memuat data.")
    st.stop()

# ---------------- replay waktu ----------------
trend = res["trend"]
iss, alerts = res["iss"], res["alerts"]
latest = True
as_of = iss["as_of"]
if len(trend) >= 2:
    with st.expander("Putar ulang waktu (replay): lihat kondisi pada waktu tertentu", icon=":material/history:"):
        st.caption("Geser untuk melihat ISS dan peringatan seolah-olah Anda memantau pada saat itu "
                   "(jendela 24 jam sebelum waktu acuan). Narasi dihitung dari keseluruhan data.")
        idx = st.select_slider(
            "Waktu acuan (WIB)", options=list(range(len(trend))), value=len(trend) - 1,
            format_func=lambda i: f"{trend['as_of'].iloc[i]:%d %b %Y %H:%M}",
        )
    if idx != len(trend) - 1:
        latest = False
        as_of = trend["as_of"].iloc[idx]
        iss = compute_iss(posts, narr, series, as_of=as_of, high_risk=meta["high_risk"])
        alerts = build_alerts(posts, narr, accounts, series, as_of=as_of, high_risk=meta["high_risk"])
if not latest:
    st.caption(f"Mode replay: menampilkan kondisi pada {pd.Timestamp(as_of):%d %b %Y %H:%M} WIB.")

# ---------------- ISS + KPI ----------------
left, right = st.columns([1, 2], gap="large")
with left:
    st.markdown("##### Indeks Siber Sosial (ISS)")
    st.plotly_chart(charts.gauge_iss(iss["iss"], iss["status"]), key="gauge")
    st.markdown(
        f"Status: {ui.status_badge(iss['status'])} &nbsp; <span class='rsd-small'>24 jam hingga "
        f"{pd.Timestamp(iss['as_of']):%d %b %H:%M} WIB · {fmt_int(iss['n_posts'])} unggahan</span>",
        unsafe_allow_html=True,
    )
with right:
    rel = relevant_narratives(narr)
    risky_narr = rel[rel["mean_risk"] >= 25] if len(rel) else rel
    n_coord = int((risky_narr["coordination"] >= C.COORD_INDICATION).sum()) if len(risky_narr) else 0
    n_bad = int((accounts["behavior_label"] == "Indikasi kuat tidak autentik").sum()) if len(accounts) else 0
    pct = 100.0 * meta["n_high_risk"] / meta["n_posts"]
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    c1.markdown(ui.kpi("Unggahan dianalisis", fmt_int(meta["n_posts"]),
                       f"{fmt_int(meta['n_accounts'])} akun · {pd.Timestamp(meta['start']):%d %b}–{pd.Timestamp(meta['end']):%d %b}",
                       "#3C9BD1"), unsafe_allow_html=True)
    c2.markdown(ui.kpi("Berisiko tinggi", fmt_int(meta["n_high_risk"]), f"{pct:.1f}% dari seluruh unggahan".replace(".", ","),
                       "#D64545"), unsafe_allow_html=True)
    c3.markdown(ui.kpi("Narasi berisiko", fmt_int(len(risky_narr)), f"{n_coord} terindikasi terkoordinasi", "#E8782B"),
                unsafe_allow_html=True)
    c4.markdown(ui.kpi("Akun terindikasi tidak autentik", fmt_int(n_bad), f"dari {fmt_int(len(accounts))} akun (perlu verifikasi manual)",
                       "#8E6BD1"), unsafe_allow_html=True)
    if latest:
        st.markdown("")
        with st.container(border=True):
            st.markdown("**Ringkasan otomatis**")
            for line in executive_summary(res):
                st.markdown(f"- {line}")

with st.expander("Bagaimana ISS dihitung?", icon=":material/calculate:"):
    comps = pd.DataFrame(iss["components"])
    if len(comps):
        comps = comps.rename(columns={"komponen": "Komponen", "bobot": "Bobot", "nilai": "Nilai (0–1)",
                                      "kontribusi": "Kontribusi ke ISS", "detail": "Keterangan"})
        st.dataframe(comps, hide_index=True)
    st.caption("ISS = 100 × Σ (bobot × nilai komponen). Status: AMAN < 25 ≤ WASPADA < 50 ≤ SIAGA < 75 ≤ AWAS. "
               "Seluruh komponen dapat diaudit; tidak ada model kotak-hitam.")

# ---------------- peringatan ----------------
st.markdown("### Peringatan dini")
if alerts:
    for a in alerts[:6]:
        st.markdown(ui.alert_card(a), unsafe_allow_html=True)
    if len(alerts) > 6:
        with st.expander(f"Lihat {len(alerts) - 6} peringatan lainnya"):
            for a in alerts[6:]:
                st.markdown(ui.alert_card(a), unsafe_allow_html=True)
else:
    st.success("Tidak ada peringatan aktif pada jendela waktu ini.", icon=":material/check_circle:")

# ---------------- grafik ----------------
g1, g2 = st.columns(2, gap="medium")
fig = charts.iss_trend_fig(trend, None if latest else as_of)
if fig is not None:
    g1.plotly_chart(fig, key="trend")
fig = charts.series_fig(series)
if fig is not None:
    g2.plotly_chart(fig, key="series")
g3, g4, g5 = st.columns([1, 1.3, 1], gap="medium")
fig = charts.category_fig(posts)
if fig is not None:
    g3.plotly_chart(fig, key="cat")
else:
    g3.info("Tidak ada konten berkategori risiko.")
fig = charts.narrative_map(risky_narr)
if fig is not None:
    g4.plotly_chart(fig, key="nmap")
else:
    g4.info("Tidak ada narasi berisiko.")
fig = charts.platform_fig(posts, meta["high_risk"])
if fig is not None:
    g5.plotly_chart(fig, key="plat")

# ---------------- prioritas tindak ----------------
st.markdown("### Prioritas tindak: 10 unggahan teratas")
st.caption("Prioritas = risiko × jangkauan (log) × bobot bila menyasar institusi. Teks ditampilkan dengan data pribadi tersamarkan.")
top = posts.sort_values(["priority", "risk"], ascending=False).head(10)
view, cfg = ui.posts_view(top)
st.dataframe(view, column_config=cfg, hide_index=True)
st.caption("Untuk menelaah satu teks secara rinci, gunakan menu Analisis Teks; untuk melihat jaringan penyebarannya, menu Narasi & Koordinasi.")
