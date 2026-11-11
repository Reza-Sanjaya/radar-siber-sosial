"""Radar Siber Sosial - titik masuk aplikasi (jalankan: streamlit run app.py)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from radar import constants as C  # noqa: E402
from radar import ui  # noqa: E402

st.set_page_config(
    page_title=f"{C.APP_NAME} - Kartika Cyber Hackathon 2026",
    page_icon=":material/radar:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": f"{C.APP_NAME} - {C.APP_TAGLINE}. Karya untuk Kartika Cyber Hackathon 2026 (kategori Siber Sosial)."},
)

pages = {
    "Pemantauan": [
        st.Page("views/home.py", title="Pusat Komando", icon=":material/radar:", default=True),
        st.Page("views/narasi.py", title="Narasi & Koordinasi", icon=":material/hub:", url_path="narasi"),
        st.Page("views/akun.py", title="Profil Akun", icon=":material/manage_accounts:", url_path="akun"),
    ],
    "Analisis": [
        st.Page("views/analisis_teks.py", title="Analisis Teks", icon=":material/manage_search:", url_path="analisis-teks"),
        st.Page("views/data_laporan.py", title="Data & Laporan", icon=":material/upload_file:", url_path="data-laporan"),
    ],
    "Proyek": [
        st.Page("views/validasi.py", title="Validasi", icon=":material/fact_check:", url_path="validasi"),
        st.Page("views/tentang.py", title="Tentang & Kepatuhan", icon=":material/verified_user:", url_path="tentang"),
    ],
}

st.logo(str(ROOT / "assets" / "logo.svg"), size="large")
nav = st.navigation(pages)
ui.ensure_state()
ui.sidebar_status()
nav.run()
