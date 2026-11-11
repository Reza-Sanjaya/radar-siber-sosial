"""Data & Laporan: pilih sumber data, atur parameter, unduh laporan SITREP dan CSV."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from radar import constants as C  # noqa: E402
from radar import ui  # noqa: E402
from radar.data import template_csv_bytes  # noqa: E402
from radar.report import (  # noqa: E402
    accounts_csv_bytes, build_report_html, fmt_int, narratives_csv_bytes, posts_csv_bytes,
)

ui.setup()
ui.hero("Data & Laporan", "Pilih sumber data, atur sensitivitas analisis, lalu unduh laporan situasi (SITREP) dan hasil dalam CSV.")

flash = st.session_state.pop("flash", None)
if flash:
    (st.success if flash[0] == "success" else st.warning)(flash[1], icon=":material/check_circle:")

ds = ui.dataset()

# ---------------- sumber data ----------------
st.markdown("### 1. Sumber data")
choice = st.radio(
    "Sumber analisis", ["Data demo (sintetis)", "Unggah data sendiri"],
    index=0 if ds["source"] == "demo" else 1, horizontal=True, label_visibility="collapsed",
)

if choice == "Data demo (sintetis)":
    if ds["source"] != "demo":
        ui.use_demo()
        st.session_state["flash"] = ("success", "Beralih ke data demo sintetis.")
        st.rerun()
    st.info(
        "Data demo berisi ±1.400 unggahan **fiktif** selama 7 hari: percakapan wajar, dua topik viral organik (kontrol), "
        "kampanye hoaks terkoordinasi, provokasi, penipuan rekrutmen, doxxing (data rekaan), dan klarifikasi resmi. "
        "Tidak ada akun, nama, nomor, atau peristiwa nyata.", icon=":material/science:",
    )
else:
    st.markdown(
        "Unggah berkas **CSV** (atau **XLSX**) berisi unggahan media sosial yang **Anda miliki izin sah untuk menganalisisnya**. "
        "Kolom wajib: `timestamp`, `account_id`, `text`. Kolom opsional: `platform`, `likes`, `shares`, `replies`, "
        "`followers`, `following`, `account_age_days`, `post_id`. Nama kolom umum berbahasa Indonesia/Inggris dikenali otomatis."
    )
    st.download_button("Unduh template CSV", template_csv_bytes(), file_name="template_unggahan.csv", mime="text/csv",
                       icon=":material/download:")
    up = st.file_uploader("Berkas data", type=["csv", "xlsx"], accept_multiple_files=False)
    anonymize = st.checkbox(
        "Anonimkan akun dan @mention (disarankan)", value=True,
        help="Nama akun diganti alias hash (AKUN-XXXXXX) dan @mention diganti @[akun]. Nomor telepon/NIK/email pada teks selalu disamarkan.",
    )
    if st.button("Analisis berkas ini", type="primary", disabled=up is None, icon=":material/play_arrow:"):
        ok, warns, errs = ui.use_upload(up.name, up.getvalue(), anonymize)
        if ok:
            msg = f"Berhasil memuat {fmt_int(len(st.session_state['ds']['df']))} baris dari {up.name}."
            if warns:
                msg += " Catatan: " + " ".join(warns)
            st.session_state["flash"] = ("success", msg)
            st.rerun()
        else:
            for e in errs:
                st.error(e, icon=":material/error:")
            for w in warns:
                st.warning(w, icon=":material/warning:")
    if ds["source"] == "upload":
        st.success(f"Data aktif: {ds['name']} ({fmt_int(len(ds['df']))} baris).", icon=":material/check_circle:")
        for w in ds.get("warnings", []):
            st.warning(w, icon=":material/warning:")

# ---------------- parameter ----------------
st.markdown("### 2. Sensitivitas analisis")
p = ui.params()
with st.expander("Atur parameter (opsional)", icon=":material/tune:"):
    with st.form("param_form"):
        c1, c2, c3 = st.columns(3)
        sim = c1.slider("Ambang kemiripan narasi", 0.30, 0.90, float(p["sim"]), 0.05,
                        help="Makin tinggi = narasi harus makin mirip (lebih ketat, narasi lebih sedikit).")
        minc = c2.slider("Ukuran narasi minimal", 2, 10, int(p["min"]), 1, help="Jumlah unggahan minimal agar disebut narasi.")
        high = c3.slider("Ambang risiko tinggi", 30, 80, int(p["high"]), 5, help="Skor risiko minimal untuk dihitung 'berisiko tinggi'.")
        applied = st.form_submit_button("Terapkan", type="primary")
    if applied:
        ui.set_params(sim, minc, high)
        st.session_state["flash"] = ("success", "Parameter diterapkan; analisis dihitung ulang.")
        st.rerun()
    if st.button("Kembalikan ke bawaan"):
        ui.set_params(C.DEFAULT_SIM_THRESHOLD, C.DEFAULT_MIN_CLUSTER, C.DEFAULT_HIGH_RISK)
        st.session_state["flash"] = ("success", "Parameter dikembalikan ke nilai bawaan.")
        st.rerun()

res = ui.get_result()
meta = res["meta"]
st.caption(f"Parameter aktif: kemiripan {meta['sim_threshold']:.2f} · narasi minimal {meta['min_cluster']} · risiko tinggi ≥ {meta['high_risk']:.0f}")

# ---------------- unduhan ----------------
st.markdown("### 3. Laporan & unduhan")
key = st.session_state.get("_res_key")
cache = st.session_state.get("_exports")
if not cache or cache[0] != key:
    with st.spinner("Menyiapkan laporan…"):
        files = {
            "html": build_report_html(res, ds["name"], anonymized=ds["anonymized"]).encode("utf-8"),
            "posts": posts_csv_bytes(res["posts"]),
            "narr": narratives_csv_bytes(res["narratives"]),
            "acc": accounts_csv_bytes(res["accounts"]),
        }
    st.session_state["_exports"] = (key, files)
files = st.session_state["_exports"][1]

d1, d2, d3, d4 = st.columns(4)
d1.download_button("Laporan SITREP (HTML)", files["html"], file_name="laporan_sitrep.html", mime="text/html",
                   icon=":material/description:", width="stretch", type="primary")
d2.download_button("Unggahan terskor (CSV)", files["posts"], file_name="hasil_unggahan.csv", mime="text/csv",
                   icon=":material/table:", width="stretch")
d3.download_button("Narasi (CSV)", files["narr"], file_name="hasil_narasi.csv", mime="text/csv",
                   icon=":material/hub:", width="stretch")
d4.download_button("Akun (CSV)", files["acc"], file_name="hasil_akun.csv", mime="text/csv",
                   icon=":material/manage_accounts:", width="stretch")
st.caption("Laporan HTML berdiri sendiri dan siap dicetak ke PDF dari peramban (Ctrl+P). Seluruh teks tersamarkan dan sel CSV "
           "diamankan dari injeksi formula Excel. Laporan memuat hash SHA-256 sebagai penanda keutuhan data.")

# ---------------- pratinjau ----------------
st.markdown("### 4. Pratinjau hasil")
posts = res["posts"]
top = posts.sort_values(["risk", "priority"], ascending=False).head(50)
view, cfg = ui.posts_view(top)
st.dataframe(view, column_config=cfg, hide_index=True)
st.caption("50 unggahan dengan risiko tertinggi. Ekspor CSV memuat seluruh unggahan beserta penjelasan skornya.")

with st.expander("Privasi & penanganan data", icon=":material/lock:"):
    st.markdown(
        "- Aplikasi **tidak melakukan scraping** dan tidak terhubung ke platform media sosial; hanya memproses berkas yang Anda unggah.\n"
        "- Data diproses **di memori sesi** dan tidak disimpan ke disk atau basis data oleh aplikasi; hilang saat sesi berakhir.\n"
        "- Analisis berjalan **sepenuhnya offline** (tanpa mengirim teks ke layanan AI/API pihak ketiga).\n"
        "- Akun dialiaskan secara default; nomor telepon, NIK, dan email pada teks disamarkan pada tampilan, laporan, dan ekspor.\n"
        "- Gunakan hanya data yang sah dan sesuai peraturan (UU PDP, kebijakan platform, dan perizinan instansi Anda)."
    )
