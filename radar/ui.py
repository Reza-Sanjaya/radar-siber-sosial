"""Komponen UI bersama untuk aplikasi Streamlit: tema, kartu, lencana, dan state data.

Aturan keamanan: seluruh teks yang berasal dari data/pengguna HARUS melewati `esc()`
sebelum dimasukkan ke HTML (`unsafe_allow_html=True`).
"""
from __future__ import annotations

import hashlib
import html
import traceback

import pandas as pd
import streamlit as st

from . import constants as C
from .data import load_csv_bytes, load_sample, standardize
from .pipeline import run_pipeline
from .report import fmt_int

DEFAULT_PARAMS = {"sim": C.DEFAULT_SIM_THRESHOLD, "min": C.DEFAULT_MIN_CLUSTER, "high": C.DEFAULT_HIGH_RISK}

CSS = """
<style>
[data-testid="stMainBlockContainer"], .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }
.rsd-hero { border: 1px solid rgba(232,184,74,.35); border-radius: 14px; padding: 22px 26px; margin-bottom: 18px;
  background: linear-gradient(120deg, rgba(47,74,60,.55), rgba(232,184,74,.10) 70%); }
.rsd-hero h1 { margin: 0 0 4px 0; font-size: 1.9rem; letter-spacing: .3px; }
.rsd-hero p { margin: 0; opacity: .85; font-size: 1.0rem; }
.rsd-card { border: 1px solid rgba(128,128,128,.28); background: rgba(128,128,128,.07); border-radius: 12px; padding: 14px 16px; }
.rsd-kpi { border: 1px solid rgba(128,128,128,.28); border-left: 4px solid var(--accent, #E8B84A);
  background: rgba(128,128,128,.07); border-radius: 10px; padding: 12px 14px; height: 100%; }
.rsd-kpi .l { font-size: .74rem; text-transform: uppercase; letter-spacing: .08em; opacity: .75; }
.rsd-kpi .v { font-size: 1.9rem; font-weight: 700; line-height: 1.15; }
.rsd-kpi .s { font-size: .8rem; opacity: .7; }
.rsd-badge { display: inline-block; border: 1px solid; border-radius: 999px; padding: 1px 10px; font-size: .78rem; font-weight: 600; }
.rsd-alert { border-left: 5px solid var(--accent, #E8B84A); background: rgba(128,128,128,.08); border-radius: 8px;
  padding: 9px 14px; margin-bottom: 8px; }
.rsd-alert .t { font-weight: 600; }
.rsd-alert .d { font-size: .86rem; opacity: .8; }
.rsd-note { border: 1px dashed rgba(232,184,74,.6); background: rgba(232,184,74,.07); border-radius: 10px; padding: 10px 14px; font-size: .9rem; }
.rsd-hl { line-height: 1.9; font-size: 1.02rem; }
.rsd-flow { display: flex; flex-wrap: wrap; gap: 8px; align-items: stretch; margin: 8px 0 4px 0; }
.rsd-step { flex: 1 1 150px; border: 1px solid rgba(128,128,128,.3); border-top: 3px solid #E8B84A; background: rgba(128,128,128,.07);
  border-radius: 10px; padding: 10px 12px; font-size: .86rem; }
.rsd-step b { display: block; margin-bottom: 3px; }
.rsd-arrow { align-self: center; opacity: .6; font-size: 1.3rem; }
.rsd-small { font-size: .82rem; opacity: .75; }
</style>
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


# --------------------------------------------------------------------------- #
# Komponen HTML
# --------------------------------------------------------------------------- #
def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="rsd-hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def kpi(label: str, value, sub: str = "", accent: str = "#E8B84A") -> str:
    return (f'<div class="rsd-kpi" style="--accent:{esc(accent)}"><div class="l">{esc(label)}</div>'
            f'<div class="v">{esc(value)}</div><div class="s">{esc(sub)}</div></div>')


def badge(text: str, color: str) -> str:
    return (f'<span class="rsd-badge" style="color:{esc(color)};border-color:{esc(color)};'
            f'background:{esc(color)}22">{esc(text)}</span>')


def level_badge(level: str) -> str:
    return badge(level, C.LEVEL_COLORS.get(level, "#8A949B"))


def status_badge(status: str) -> str:
    return badge(status, C.STATUS_COLORS.get(status, "#8A949B"))


def alert_card(alert: dict) -> str:
    color = C.STATUS_COLORS.get(alert["level"], "#8A949B")
    return (f'<div class="rsd-alert" style="--accent:{color}">{badge(alert["level"], color)} '
            f'<span class="t">{esc(alert["title"])}</span><div class="d">{esc(alert["detail"])}</div></div>')


def note(text: str) -> None:
    st.markdown(f'<div class="rsd-note">{esc(text)}</div>', unsafe_allow_html=True)


def flow(steps: list[tuple[str, str]]) -> None:
    parts = []
    for i, (title, body) in enumerate(steps):
        if i:
            parts.append('<div class="rsd-arrow">➜</div>')
        parts.append(f'<div class="rsd-step"><b>{esc(title)}</b>{esc(body)}</div>')
    st.markdown(f'<div class="rsd-flow">{"".join(parts)}</div>', unsafe_allow_html=True)


def empty_state(message: str) -> None:
    st.info(message, icon=":material/info:")


# --------------------------------------------------------------------------- #
# State data & parameter
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _demo_df() -> pd.DataFrame:
    res = load_sample()
    return res.df


@st.cache_data(show_spinner=False, max_entries=8)
def _run_demo(sim: float, min_cluster: int, high: float) -> dict:
    return run_pipeline(_demo_df(), sim_threshold=sim, min_cluster=min_cluster, high_risk=high)


def _dataset_id(df: pd.DataFrame, name: str) -> str:
    h = hashlib.sha1(f"{name}|{len(df)}|{df['timestamp'].min()}|{df['timestamp'].max()}".encode()).hexdigest()[:10]
    return h


def use_demo() -> None:
    df = _demo_df()
    st.session_state["ds"] = {
        "id": "demo", "name": "Data demo sintetis (fiktif)", "source": "demo", "df": df,
        "anonymized": True, "warnings": [],
    }


def use_upload(name: str, data: bytes, anonymize: bool = True) -> tuple[bool, list[str], list[str]]:
    """Muat berkas unggahan. Mengembalikan (berhasil, peringatan, galat). Tidak melempar exception."""
    lower = (name or "").lower()
    try:
        if lower.endswith((".xlsx", ".xlsm")):
            import io

            raw = pd.read_excel(io.BytesIO(data), dtype=str)
            res = standardize(raw, anonymize=anonymize)
        else:
            res = load_csv_bytes(data, anonymize=anonymize)
    except Exception as exc:  # berkas rusak, format tak didukung, dsb.
        return False, [], [f"Berkas tidak dapat diproses: {type(exc).__name__}: {exc}"]
    if not res.ok:
        return False, res.warnings, res.errors
    st.session_state["ds"] = {
        "id": _dataset_id(res.df, name), "name": f"Unggahan: {name}", "source": "upload", "df": res.df,
        "anonymized": anonymize, "warnings": res.warnings,
    }
    return True, res.warnings, []


def ensure_state() -> None:
    if "params" not in st.session_state:
        st.session_state["params"] = dict(DEFAULT_PARAMS)
    if "ds" not in st.session_state:
        use_demo()


def params() -> dict:
    ensure_state()
    return st.session_state["params"]


def set_params(sim: float, min_cluster: int, high: float) -> None:
    st.session_state["params"] = {"sim": float(sim), "min": int(min_cluster), "high": float(high)}


def dataset() -> dict:
    ensure_state()
    return st.session_state["ds"]


def get_result() -> dict:
    """Hasil analisis untuk dataset aktif (dihitung ulang hanya bila dataset/parameter berubah)."""
    ensure_state()
    ds, p = st.session_state["ds"], st.session_state["params"]
    key = (ds["id"], p["sim"], p["min"], p["high"])
    if st.session_state.get("_res_key") != key or "_res" not in st.session_state:
        try:
            with st.spinner("Menganalisis data…"):
                if ds["source"] == "demo":
                    res = _run_demo(p["sim"], p["min"], p["high"])
                else:
                    res = run_pipeline(ds["df"], sim_threshold=p["sim"], min_cluster=p["min"], high_risk=p["high"])
        except Exception as exc:  # jaring pengaman: jangan biarkan halaman crash
            st.error(f"Analisis gagal ({type(exc).__name__}). Kembali ke data demo.", icon=":material/error:")
            with st.expander("Detail teknis"):
                st.code(traceback.format_exc()[-1500:])
            use_demo()
            ds = st.session_state["ds"]
            res = _run_demo(p["sim"], p["min"], p["high"])
            key = (ds["id"], p["sim"], p["min"], p["high"])
        st.session_state["_res"] = res
        st.session_state["_res_key"] = key
    return st.session_state["_res"]


def setup() -> None:
    """Dipanggil di awal setiap halaman: CSS + state."""
    ensure_state()
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_status() -> None:
    ds = dataset()
    p = params()
    st.sidebar.markdown("---")
    tag = "Data demo (sintetis)" if ds["source"] == "demo" else "Data unggahan"
    st.sidebar.caption(f"**Sumber aktif:** {tag}")
    if ds["source"] == "upload":
        st.sidebar.caption(ds["name"])
    st.sidebar.caption(f"{fmt_int(len(ds['df']))} unggahan · ambang risiko tinggi ≥ {p['high']:.0f}")


# --------------------------------------------------------------------------- #
# Tabel tampilan
# --------------------------------------------------------------------------- #
def posts_view(posts: pd.DataFrame, limit: int | None = None) -> tuple[pd.DataFrame, dict]:
    """DataFrame siap tampil (teks tersamarkan) + column_config."""
    d = posts if limit is None else posts.head(limit)
    view = pd.DataFrame(
        {
            "Waktu": d["timestamp"],
            "Akun": d["account_id"],
            "Platform": d["platform"],
            "Kategori": d["label"],
            "Risiko": d["risk"],
            "Prioritas": d["priority"],
            "Narasi": d["narrative"],
            "Teks (tersamarkan)": d["text_display"],
        }
    )
    cfg = {
        "Waktu": st.column_config.DatetimeColumn(format="DD MMM HH:mm"),
        "Risiko": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Prioritas": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Teks (tersamarkan)": st.column_config.TextColumn(width="large"),
    }
    return view, cfg
