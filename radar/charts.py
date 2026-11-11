"""Pembuat grafik Plotly. Semua fungsi mengembalikan Figure atau None bila data kosong.

Warna teks/latar mengikuti tema Streamlit (st.plotly_chart theme="streamlit");
di sini hanya warna data (kategori, level, status) yang ditetapkan eksplisit.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import constants as C

_MARGIN = dict(l=10, r=14, t=40, b=40)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def gauge_iss(score: float, status: str) -> go.Figure:
    color = C.STATUS_COLORS.get(status, "#888888")
    bands = list(C.STATUS_LEVELS) + [("_", 100.0)]
    steps = []
    for (name, low), (_, high) in zip(bands[:-1], bands[1:]):
        steps.append({"range": [low, high], "color": _rgba(C.STATUS_COLORS[name], 0.28)})
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(score),
            number={"font": {"size": 54}, "valueformat": ".0f"},
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, 25, 50, 75, 100]},
                "bar": {"color": color, "thickness": 0.28},
                "steps": steps,
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(height=250, margin=dict(l=30, r=40, t=20, b=0))
    return fig


def iss_trend_fig(trend: pd.DataFrame, as_of=None) -> go.Figure | None:
    if trend is None or len(trend) == 0:
        return None
    fig = go.Figure()
    for (name, low), (_, high) in zip(list(C.STATUS_LEVELS), list(C.STATUS_LEVELS[1:]) + [("_", 100.0)]):
        fig.add_hrect(y0=low, y1=high, fillcolor=_rgba(C.STATUS_COLORS[name], 0.10), line_width=0, layer="below")
    fig.add_trace(
        go.Scatter(
            x=trend["as_of"], y=trend["iss"], mode="lines+markers", name="ISS",
            line=dict(color="#E8B84A", width=2.5), marker=dict(size=6),
            customdata=trend["status"], hovertemplate="%{x|%d %b %H:%M}<br>ISS %{y:.0f} (%{customdata})<extra></extra>",
        )
    )
    if as_of is not None:
        fig.add_vline(x=pd.Timestamp(as_of), line=dict(color="#9AA5A0", width=1.5, dash="dot"))
    fig.update_yaxes(range=[0, 100], title="ISS")
    fig.update_layout(height=280, margin=_MARGIN, showlegend=False, title="Tren Indeks Siber Sosial")
    return fig


def series_fig(series: pd.DataFrame) -> go.Figure | None:
    if series is None or len(series) == 0:
        return None
    s = series.reset_index()
    first = s.columns[0]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s[first], y=s["volume"], name="Semua unggahan", marker_color=_rgba("#8A949B", 0.55)))
    fig.add_trace(go.Bar(x=s[first], y=s["risky"], name="Berisiko tinggi", marker_color="#D64545"))
    anom = s[s["anom_risky"] | s["anom_volume"]]
    if len(anom):
        fig.add_trace(
            go.Scatter(
                x=anom[first], y=anom["volume"], mode="markers", name="Anomali",
                marker=dict(symbol="triangle-down", size=11, color="#E8B84A", line=dict(width=1, color="#000000")),
                hovertemplate="Anomali %{x|%d %b %H:%M}<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="overlay", height=280, margin=_MARGIN, title="Volume & konten berisiko (dengan penanda anomali)",
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0, title_text=""),
    )
    return fig


def category_fig(posts: pd.DataFrame) -> go.Figure | None:
    if posts is None or len(posts) == 0:
        return None
    vc = posts["label"].value_counts()
    vc = vc[[i for i in vc.index if i != C.CAT_NETRAL]]
    if len(vc) == 0:
        return None
    fig = go.Figure(
        go.Pie(
            labels=list(vc.index), values=list(vc.values), hole=0.55,
            marker=dict(colors=[C.CAT_COLORS.get(k, "#888888") for k in vc.index]),
            textinfo="value", sort=False,
            hovertemplate="%{label}: %{value} unggahan (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(height=290, margin=_MARGIN, title="Sebaran kategori (tanpa Netral)",
                      legend=dict(orientation="h", yanchor="top", y=-0.04, title_text=""))
    return fig


def narrative_map(narr: pd.DataFrame) -> go.Figure | None:
    if narr is None or len(narr) == 0:
        return None
    d = narr.copy()
    d["ukuran_gelembung"] = np.sqrt(d["size"].astype(float))
    fig = px.scatter(
        d, x="first_seen", y="mean_risk", size="ukuran_gelembung", color="top_label",
        color_discrete_map=C.CAT_COLORS, size_max=38,
        hover_name="narrative",
        hover_data={"size": True, "n_accounts": True, "coordination": ":.0f", "coord_label": True,
                    "ukuran_gelembung": False, "first_seen": "|%d %b %H:%M", "mean_risk": ":.0f", "top_label": False},
        labels={"first_seen": "Pertama terlihat", "mean_risk": "Rata-rata risiko", "top_label": "Kategori",
                "size": "Unggahan", "n_accounts": "Akun", "coordination": "Skor koordinasi", "coord_label": "Label"},
    )
    fig.update_yaxes(range=[-5, 105])
    fig.update_layout(height=290, margin=_MARGIN, title="Peta narasi (ukuran = jumlah unggahan)",
                      legend=dict(orientation="h", yanchor="top", y=-0.18, title_text=""))
    return fig


def narrative_timeline(sub: pd.DataFrame) -> go.Figure | None:
    """Setiap titik = satu unggahan; sumbu-y = akun (urut kemunculan pertama). Panel atas = jumlah unggahan per waktu."""
    if sub is None or len(sub) == 0:
        return None
    d = sub.sort_values("timestamp").copy()
    order = {a: i for i, a in enumerate(d["account_id"].drop_duplicates())}
    d["urutan_akun"] = d["account_id"].map(order)
    teks = d["text_display"].astype(str).str.slice(0, 90).tolist()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.22, 0.78], vertical_spacing=0.03)
    fig.add_trace(go.Histogram(x=d["timestamp"], nbinsx=40, marker_color=_rgba("#8A949B", 0.7), name="Unggahan", showlegend=False,
                               hovertemplate="%{x|%d %b %H:%M}<br>%{y} unggahan<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=d["timestamp"], y=d["urutan_akun"], mode="markers", showlegend=False,
        marker=dict(size=8, color=d["risk"].astype(float), colorscale="YlOrRd", cmin=0, cmax=100,
                    colorbar=dict(title="Risiko", thickness=10), line=dict(width=0.5, color="rgba(0,0,0,0.35)")),
        customdata=list(zip(d["account_id"].astype(str), teks, d["risk"].astype(float))),
        hovertemplate="%{x|%d %b %H:%M:%S}<br>%{customdata[0]}<br>Risiko %{customdata[2]:.0f}<br>%{customdata[1]}<extra></extra>",
    ), row=2, col=1)
    fig.update_yaxes(title_text="Akun (urut muncul)", row=2, col=1)
    fig.update_yaxes(title_text="Jumlah", row=1, col=1)
    fig.update_xaxes(title_text="Waktu", row=2, col=1)
    fig.update_layout(height=380, margin=_MARGIN)
    return fig


def components_fig(comp: dict) -> go.Figure | None:
    items = [(k, v) for k, v in comp.items() if v is not None]
    if not items:
        return None
    names = [k for k, _ in items]
    vals = [round(100 * float(v), 1) for _, v in items]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color="#E8B84A",
                           text=[f"{v:.0f}" for v in vals], textposition="outside"))
    fig.update_xaxes(range=[0, 115], title="Nilai komponen (0-100)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=230, margin=_MARGIN, title="Komponen skor koordinasi")
    return fig


def category_scores_fig(cat_scores: dict) -> go.Figure:
    cats = list(cat_scores.keys())
    vals = [float(cat_scores[c]) for c in cats]
    fig = go.Figure(go.Bar(x=vals, y=cats, orientation="h", marker_color=[C.CAT_COLORS.get(c, "#888") for c in cats],
                           text=[f"{v:.0f}" for v in vals], textposition="outside"))
    fig.update_xaxes(range=[0, 115], title="Skor kategori (0-100)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=250, margin=_MARGIN, title="Skor per kategori")
    return fig


def account_scatter(accounts: pd.DataFrame) -> go.Figure | None:
    if accounts is None or len(accounts) == 0:
        return None
    d = accounts.dropna(subset=["account_age_days", "followers", "following"]).copy()
    if len(d) == 0:
        return None
    d["rasio"] = (d["following"] + 1.0) / (d["followers"] + 1.0)
    d["umur_plot"] = d["account_age_days"].clip(lower=1)
    color_map = {"Normal": "#2E9E6B", "Perlu dipantau": "#D9A62E", "Indikasi kuat tidak autentik": "#D64545"}
    fig = px.scatter(
        d, x="umur_plot", y="rasio", color="behavior_label", size="posts", size_max=18, log_x=True, log_y=True,
        color_discrete_map=color_map, hover_name="account_id",
        hover_data={"behavior": ":.0f", "posts": True, "umur_plot": False, "rasio": ":.1f", "behavior_label": False},
        labels={"umur_plot": "Umur akun (hari, log)", "rasio": "Mengikuti : pengikut (log)", "behavior": "Skor perilaku",
                "posts": "Unggahan", "behavior_label": "Label"},
    )
    fig.update_layout(height=340, margin=_MARGIN, title="Profil akun: umur vs rasio mengikuti/pengikut",
                      legend=dict(orientation="h", yanchor="top", y=-0.2, title_text=""))
    return fig


def platform_fig(posts: pd.DataFrame, high_risk: float) -> go.Figure | None:
    if posts is None or len(posts) == 0:
        return None
    d = posts.assign(berisiko=posts["risk"] >= high_risk)
    g = d.groupby("platform")["berisiko"].agg(["sum", "size"]).reset_index()
    g["aman"] = g["size"] - g["sum"]
    g = g.sort_values("size", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=g["platform"], y=g["aman"], name="Lainnya", marker_color=_rgba("#8A949B", 0.55)))
    fig.add_trace(go.Bar(x=g["platform"], y=g["sum"], name="Berisiko tinggi", marker_color="#D64545"))
    fig.update_layout(barmode="stack", height=290, margin=_MARGIN, title="Unggahan per platform",
                      legend=dict(orientation="h", yanchor="top", y=-0.16, x=0, title_text=""))
    return fig


def evaluation_fig(per_cat: pd.DataFrame) -> go.Figure | None:
    if per_cat is None or len(per_cat) == 0:
        return None
    colors = [C.CAT_COLORS.get(k, "#888") for k in per_cat["kategori"]]
    fig = go.Figure(go.Bar(
        x=[round(100 * v, 1) for v in per_cat["nilai"]], y=per_cat["kategori"], orientation="h", marker_color=colors,
        text=[f"{100 * v:.0f}% ({int(t)}/{int(n)})" for v, t, n in zip(per_cat["nilai"], per_cat["terdeteksi"], per_cat["jumlah"])],
        textposition="outside",
    ))
    fig.update_xaxes(range=[0, 125], title="%")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=320, margin=_MARGIN, title="Kinerja per kategori pada himpunan uji")
    return fig


def safe_float(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default
