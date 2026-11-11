"""Laporan situasi (SITREP) HTML mandiri + ekspor CSV.

Prinsip:
  * Semua teks dari data di-escape (tidak ada HTML/skrip yang lolos ke laporan).
  * Hanya teks tersamarkan (`text_display`) yang masuk laporan/ekspor.
  * Sel CSV yang diawali = + - @ diberi tanda kutip agar tidak dieksekusi sebagai
    formula oleh Excel/LibreOffice (CSV/formula injection).
  * Laporan memuat hash SHA-256 data ekspor sebagai penanda keutuhan bukti.
"""
from __future__ import annotations

import hashlib
import html
import io
from datetime import datetime

import pandas as pd

from . import constants as C
from .playbook import SLA, recommend

_FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def _safe_cell(value):
    if isinstance(value, str) and value and value[0] in _FORMULA_PREFIX:
        return "'" + value
    return value


def sanitize_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].map(_safe_cell)
    return out


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    sanitize_for_csv(df).to_csv(buf, index=False)
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM agar Excel membaca UTF-8


def posts_export(posts: pd.DataFrame) -> pd.DataFrame:
    if len(posts) == 0:
        return pd.DataFrame(columns=["id_unggahan", "waktu", "platform", "akun", "teks_tersamarkan", "skor_risiko",
                                     "level", "kategori", "isyarat", "narasi", "prioritas", "jangkauan", "penjelasan"])
    out = pd.DataFrame(
        {
            "id_unggahan": posts["post_id"],
            "waktu": posts["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": posts["platform"],
            "akun": posts["account_id"],
            "teks_tersamarkan": posts["text_display"],
            "skor_risiko": posts["risk"],
            "level": posts["level"],
            "kategori": posts["label"],
            "isyarat": posts["cues"],
            "narasi": posts["narrative"],
            "prioritas": posts["priority"],
            "jangkauan": posts["reach"],
            "penjelasan": posts["explanation"],
        }
    )
    return out


def posts_csv_bytes(posts: pd.DataFrame) -> bytes:
    return _to_csv_bytes(posts_export(posts))


def narratives_csv_bytes(narratives: pd.DataFrame) -> bytes:
    if len(narratives) == 0:
        return _to_csv_bytes(pd.DataFrame(columns=["narasi"]))
    cols = ["narrative", "size", "n_accounts", "first_seen", "last_seen", "mean_risk", "top_label", "coordination",
            "coord_label", "priority", "hashtags", "sample_text"]
    out = narratives[cols].copy()
    out["first_seen"] = out["first_seen"].dt.strftime("%Y-%m-%d %H:%M")
    out["last_seen"] = out["last_seen"].dt.strftime("%Y-%m-%d %H:%M")
    out.columns = ["narasi", "jumlah_unggahan", "jumlah_akun", "pertama_terlihat", "terakhir_terlihat",
                   "rata_rata_risiko", "kategori_dominan", "skor_koordinasi", "label_koordinasi", "prioritas",
                   "tagar", "contoh_teks_tersamarkan"]
    return _to_csv_bytes(out)


def accounts_csv_bytes(accounts: pd.DataFrame) -> bytes:
    if len(accounts) == 0:
        return _to_csv_bytes(pd.DataFrame(columns=["akun"]))
    cols = ["account_id", "posts", "mean_risk", "high_risk_posts", "narratives", "behavior", "behavior_label",
            "evidence", "review_priority"]
    out = accounts[cols].copy()
    out.columns = ["akun_alias", "unggahan", "rata_rata_risiko", "unggahan_berisiko_tinggi", "narasi_terkait",
                   "skor_perilaku", "label_perilaku", "kecukupan_bukti", "prioritas_tinjauan"]
    return _to_csv_bytes(out)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Ringkasan otomatis
# --------------------------------------------------------------------------- #
def relevant_narratives(narratives: pd.DataFrame) -> pd.DataFrame:
    """Narasi yang layak diperhatikan: berisiko atau terindikasi koordinasi."""
    if len(narratives) == 0:
        return narratives
    m = (narratives["mean_risk"] >= 25) | (narratives["coordination"] >= C.COORD_INDICATION)
    return narratives[m].reset_index(drop=True)


def fmt_int(n) -> str:
    """Angka bulat dengan pemisah ribuan gaya Indonesia (1.377)."""
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def _pct(part: float, whole: float) -> str:
    return f"{(100.0 * part / whole):.1f}%".replace(".", ",") if whole else "0%"


def executive_summary(result: dict) -> list[str]:
    """Kalimat ringkasan eksekutif yang dibangkitkan dari hasil analisis (tanpa model bahasa)."""
    meta, iss, posts = result["meta"], result["iss"], result["posts"]
    if meta["n_posts"] == 0:
        return ["Tidak ada data untuk diringkas."]
    lines = [
        f"Status Indeks Siber Sosial (ISS) berada pada tingkat **{iss['status']}** (skor {iss['iss']:.0f}/100) "
        f"untuk 24 jam terakhir hingga {pd.Timestamp(iss['as_of']):%d %b %Y %H:%M} WIB."
    ]
    n_high = meta["n_high_risk"]
    lines.append(
        f"Dari {fmt_int(meta['n_posts'])} unggahan oleh {fmt_int(meta['n_accounts'])} akun, {fmt_int(n_high)} unggahan "
        f"({_pct(n_high, meta['n_posts'])}) berskor risiko ≥ {meta['high_risk']:.0f}."
    )
    risky = posts[posts["risk"] >= meta["high_risk"]]
    if len(risky):
        top = risky["label"].value_counts().head(3)
        parts = ", ".join(f"{k} ({v})" for k, v in top.items())
        lines.append(f"Kategori ancaman terbanyak: {parts}.")
    rel = relevant_narratives(result["narratives"])
    risky_n = rel[rel["mean_risk"] >= 25] if len(rel) else rel
    if len(risky_n):
        best = risky_n.sort_values("priority", ascending=False).iloc[0]
        lines.append(
            f"Terdapat {len(risky_n)} narasi berisiko; prioritas tertinggi {best['narrative']} "
            f"({best['top_label']}, {int(best['size'])} unggahan dari {int(best['n_accounts'])} akun, "
            f"skor koordinasi {best['coordination']:.0f}, label: {best['coord_label']})."
        )
    n_alert = len(result["alerts"])
    if n_alert:
        top_alert = result["alerts"][0]
        lines.append(f"Terdapat {n_alert} peringatan aktif; tertinggi: [{top_alert['level']}] {top_alert['title']}.")
    lines.append("Seluruh temuan adalah indikasi untuk prioritas tinjauan; keputusan akhir tetap pada petugas.")
    return lines


# --------------------------------------------------------------------------- #
# Laporan HTML
# --------------------------------------------------------------------------- #
def _e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def _md_bold(text: str) -> str:
    """Konversi **teks** menjadi <b> setelah di-escape."""
    parts = _e(text).split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def _table(headers: list[str], rows: list[list[str]], raw_cols: set[int] | None = None) -> str:
    raw_cols = raw_cols or set()
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c if i in raw_cols else _e(c)}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows
    )
    if not rows:
        body = f'<tr><td colspan="{len(headers)}" class="muted">Tidak ada data.</td></tr>'
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _chip(text: str, color: str) -> str:
    return f'<span class="chip" style="background:{color}22;border-color:{color};color:{color}">{_e(text)}</span>'


_CSS = """
body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1c2521;background:#f4f6f4;margin:0;padding:24px}
.page{max-width:980px;margin:0 auto;background:#fff;border:1px solid #d7ddd9;border-radius:10px;padding:32px 38px}
h1{font-size:22px;margin:0 0 4px;letter-spacing:.5px} h2{font-size:16px;margin:28px 0 8px;border-bottom:2px solid #2f4a3c;padding-bottom:4px;color:#2f4a3c}
.sub{color:#5b6a62;font-size:13px}.muted{color:#7b8780}
.banner{display:flex;gap:16px;align-items:center;background:#f0f4f1;border:1px solid #d7ddd9;border-radius:8px;padding:14px 18px;margin:16px 0}
.big{font-size:38px;font-weight:700;line-height:1}
.chip{display:inline-block;border:1px solid;border-radius:999px;padding:1px 10px;font-size:12px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
th{background:#2f4a3c;color:#fff;text-align:left;padding:6px 8px;font-weight:600}
td{border-bottom:1px solid #e3e8e5;padding:6px 8px;vertical-align:top}
ul{margin:6px 0 6px 18px;padding:0;font-size:13.5px} li{margin:3px 0}
.note{background:#fff8e6;border:1px solid #ecd9a0;border-radius:8px;padding:10px 14px;font-size:12.5px;margin-top:20px}
.foot{font-size:11.5px;color:#7b8780;margin-top:24px;word-break:break-all}
@media print{body{background:#fff;padding:0}.page{border:0;padding:0}}
"""


def build_report_html(result: dict, dataset_name: str = "Data", anonymized: bool = True,
                      generated_at: datetime | None = None, top_n: int = 10) -> str:
    """Laporan situasi mandiri (satu berkas HTML, siap cetak ke PDF)."""
    generated_at = generated_at or datetime.now()
    meta, iss, posts = result["meta"], result["iss"], result["posts"]
    narr, accounts, alerts = result["narratives"], result["accounts"], result["alerts"]
    status_color = C.STATUS_COLORS.get(iss["status"], "#888")

    period = "-"
    if meta["start"] is not None:
        period = f"{pd.Timestamp(meta['start']):%d %b %Y %H:%M} s.d. {pd.Timestamp(meta['end']):%d %b %Y %H:%M} WIB"

    summary_li = "".join(f"<li>{_md_bold(s)}</li>" for s in executive_summary(result))

    alert_rows = [
        [_chip(a["level"], C.STATUS_COLORS.get(a["level"], "#888")), a["title"], a["detail"]] for a in alerts
    ]
    rel = relevant_narratives(narr)
    rel = rel[rel["mean_risk"] >= 25] if len(rel) else rel
    narr_rows = []
    narr_actions = ""
    if len(rel):
        for _, n in rel.sort_values("priority", ascending=False).head(6).iterrows():
            narr_rows.append([
                n["narrative"], n["top_label"], f"{int(n['size'])} / {int(n['n_accounts'])}",
                f"{n['mean_risk']:.0f}", f"{n['coordination']:.0f} - {n['coord_label']}", f"{n['priority']:.0f}",
                n["sample_text"],
            ])
        top = rel.sort_values("priority", ascending=False).iloc[0]
        rec = recommend(top["top_label"], C.risk_level(top["mean_risk"]), int(top["n_accounts"]), top["coord_label"],
                        top["tni_share"] >= 0.5)
        steps = "".join(f"<li>{_e(s)}</li>" for s in rec["steps"])
        narr_actions = (f"<p class='sub'>Rekomendasi tindakan untuk narasi prioritas <b>{_e(top['narrative'])}</b> "
                        f"({_e(SLA.get(C.risk_level(top['mean_risk']), ''))}; unit: {_e(rec['unit'])}):</p><ul>{steps}</ul>")

    post_rows = []
    if len(posts):
        for _, p in posts.nlargest(top_n, "priority").iterrows():
            post_rows.append([f"{p['timestamp']:%d %b %H:%M}", p["account_id"], p["label"], f"{p['risk']:.0f}",
                              f"{p['priority']:.0f}", p["text_display"]])

    acc_rows = []
    if len(accounts):
        for _, a in accounts.head(8).iterrows():
            acc_rows.append([a["account_id"], int(a["posts"]), f"{a['mean_risk']:.0f}", f"{a['behavior']:.0f}",
                             a["behavior_label"], a["evidence"]])

    cat_rows = []
    if len(posts):
        vc = posts["label"].value_counts()
        for lab, n in vc.items():
            cat_rows.append([lab, int(n), _pct(n, len(posts))])

    data_hash = sha256_hex(posts_csv_bytes(posts))
    anon_text = "Identitas akun telah diganti alias (pseudonim)." if anonymized else (
        "PERHATIAN: identitas akun pada data sumber tidak dialiaskan; perlakukan laporan ini sebagai dokumen terbatas.")

    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laporan Situasi Siber Sosial</title><style>{_CSS}</style></head><body><div class="page">
<h1>LAPORAN SITUASI SIBER SOSIAL (SITREP)</h1>
<div class="sub">Dihasilkan oleh {_e(C.APP_NAME)} · Sumber data: {_e(dataset_name)} · Periode: {_e(period)} ·
Dibuat: {generated_at:%d %b %Y %H:%M} WIB</div>
<div class="banner"><div class="big" style="color:{status_color}">{iss['iss']:.0f}</div>
<div><div>Indeks Siber Sosial (ISS) {_chip(iss['status'], status_color)}</div>
<div class="sub">{fmt_int(meta['n_posts'])} unggahan · {fmt_int(meta['n_accounts'])} akun · {fmt_int(meta['n_high_risk'])} berisiko tinggi · {meta['n_narratives']} narasi</div></div></div>
<h2>1. Ringkasan Eksekutif</h2><ul>{summary_li}</ul>
<h2>2. Peringatan Aktif</h2>{_table(['Level', 'Peringatan', 'Rincian'], alert_rows, raw_cols={0})}
<h2>3. Narasi Prioritas</h2>
{_table(['ID', 'Kategori', 'Unggahan / Akun', 'Risiko', 'Koordinasi', 'Prioritas', 'Contoh teks'], narr_rows)}
{narr_actions}
<h2>4. Unggahan Prioritas Tindak</h2>
{_table(['Waktu', 'Akun (alias)', 'Kategori', 'Risiko', 'Prioritas', 'Teks (tersamarkan)'], post_rows)}
<h2>5. Akun yang Perlu Verifikasi Manual</h2>
{_table(['Akun (alias)', 'Unggahan', 'Risiko rata-rata', 'Skor perilaku', 'Label', 'Bukti'], acc_rows)}
<p class="sub">Skor perilaku hanyalah indikasi tidak autentik; tidak ada upaya mengungkap identitas pemilik akun.</p>
<h2>6. Sebaran Kategori</h2>{_table(['Kategori', 'Jumlah', 'Porsi'], cat_rows)}
<h2>7. Metodologi & Keterbatasan</h2>
<ul>
<li>Skor risiko berbasis kamus isyarat yang transparan (disinformasi, provokasi/SARA, kekerasan, penipuan, doxxing) + aturan ko-okurensi, penanganan negasi, dan penahan klarifikasi/cek fakta.</li>
<li>Narasi dikelompokkan dengan kemiripan teks (Jaccard); Skor Koordinasi menggabungkan kepadatan waktu, keragaman akun, kemiripan teks, umur akun, dan akun lintas-narasi.</li>
<li>ISS = gabungan berbobot: porsi konten berisiko tinggi (30%), lonjakan anomali (20%), narasi terkoordinasi aktif (25%), prioritas unggahan teratas (15%), konten berisiko menyasar institusi (10%).</li>
<li>Keterbatasan: pendekatan berbasis kamus lemah pada kalimat tanpa isyarat eksplisit, sarkasme, dan bahasa daerah; dapat menghasilkan false positive/negative.</li>
<li>{_e(anon_text)} Nomor telepon, NIK, dan email pada teks telah disamarkan.</li></ul>
<div class="note"><b>Catatan penggunaan.</b> Dokumen ini dibangkitkan otomatis sebagai bahan pertimbangan dan WAJIB diverifikasi oleh petugas berwenang
sebelum ada tindakan. Sistem tidak mengambil tindakan otomatis terhadap akun atau konten mana pun.</div>
<div class="foot">Parameter: ambang kemiripan {meta['sim_threshold']:.2f}, ukuran narasi minimal {meta['min_cluster']}, ambang risiko tinggi {meta['high_risk']:.0f}.<br>
SHA-256 data unggahan terproses (CSV ekspor): {data_hash}</div>
</div></body></html>"""
