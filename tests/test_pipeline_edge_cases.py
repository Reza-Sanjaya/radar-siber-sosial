"""Uji ketahanan pipeline + laporan pada data kecil, ekstrem, dan berbahaya."""
import numpy as np
import pandas as pd
import pytest

from radar import data as D
from radar.pipeline import run_pipeline
from radar.report import (
    accounts_csv_bytes, build_report_html, executive_summary, narratives_csv_bytes, posts_csv_bytes,
)


def _std(rows, cols=("timestamp", "account_id", "text"), anonymize=True):
    res = D.standardize(pd.DataFrame(rows, columns=list(cols)), anonymize=anonymize)
    assert res.ok, res.errors
    return res.df


def _exercise(df):
    res = run_pipeline(df)
    html = build_report_html(res, "uji", anonymized=True)
    assert "<html" in html.lower()
    posts_csv_bytes(res["posts"]); narratives_csv_bytes(res["narratives"]); accounts_csv_bytes(res["accounts"])
    executive_summary(res)
    return res, html


def test_satu_baris():
    _exercise(_std([["2026-11-01 10:00:00", "a", "halo dunia"]]))


def test_dua_baris_waktu_sama():
    _exercise(_std([["2026-11-01 10:00:00", "a", "halo"], ["2026-11-01 10:00:00", "b", "halo"]]))


def test_semua_teks_identik_waktu_sama():
    rows = [["2026-11-01 10:00:00", f"akun{i}", "SEBARKAN!!! media bungkam, sebelum dihapus"] for i in range(40)]
    res, _ = _exercise(_std(rows))
    assert res["narratives"]["coordination"].max() > 40


def test_satu_akun_spam():
    rows = [[f"2026-11-01 10:{i:02d}:00", "spammer", "Slot gacor klik link bit.ly/x deposit receh"] for i in range(30)]
    _exercise(_std(rows))


def test_tanpa_kolom_opsional_dan_rentang_sangat_pendek():
    rows = [[f"2026-11-01 10:00:{i:02d}", f"a{i}", f"teks nomor {i} yang berbeda-beda sekali"] for i in range(30)]
    _exercise(_std(rows))


def test_rentang_bertahun_tahun():
    rows = [[f"{2020 + i % 6}-0{1 + i % 9}-15 10:00:00", f"a{i}", f"cerita {i}"] for i in range(60)]
    _exercise(_std(rows))


def test_teks_ekstrem_dan_berbahaya():
    jahat = [
        "<script>alert('xss')</script> SEBARKAN sebelum dihapus",
        "=cmd|' /C calc'!A0 SEBARKAN",
        "+SUM(1+1) klik link bit.ly/x",
        "@HYPERLINK(\"http://evil\") hadiah anda menang",
        "😀" * 500,
        "a" * 5000,
        "‮\u0000 teks bidi aneh",
        "NIK 3500000000000123 telp 081200001234 alamat rumah sebar data",
    ]
    rows = [[f"2026-11-01 10:{i:02d}:00", f"=akun{i}", t] for i, t in enumerate(jahat)]
    res, html = _exercise(_std(rows))
    assert "<script>alert" not in html
    assert "3500000000000123" not in html and "081200001234" not in html
    csv_text = posts_csv_bytes(res["posts"]).decode("utf-8-sig")
    for line in csv_text.splitlines()[1:]:
        for cell in line.split(","):
            assert not cell.startswith(("=", "+", "@")), cell


def test_kolom_numerik_kotor():
    df = pd.DataFrame({
        "timestamp": ["2026-11-01 10:00:00", "2026-11-01 11:00:00", "2026-11-01 12:00:00"],
        "account_id": ["a", "b", "c"], "text": ["x halo", "y halo", "z halo"],
        "likes": ["abc", "-5", "1e3"], "followers": [None, "NaN", "100"], "account_age_days": ["-1", "", "9999999"],
    })
    res = D.standardize(df)
    assert res.ok
    _exercise(res.df)


def test_parameter_ekstrem():
    df = D.load_sample().df
    for sim, mn, high in [(0.3, 2, 30), (0.9, 10, 80)]:
        res = run_pipeline(df, sim_threshold=sim, min_cluster=mn, high_risk=high)
        build_report_html(res, "uji", anonymized=True)


def test_data_demo_hasil_yang_diharapkan():
    res = run_pipeline(D.load_sample().df)
    n = res["narratives"]
    top = n.sort_values("priority", ascending=False).iloc[0]
    assert top["top_label"] == "Disinformasi" and top["coord_label"] == "Terkoordinasi kuat"
    assert res["iss"]["status"] in {"SIAGA", "AWAS"}
    # kontrol organik (olahraga/diskon) tidak boleh ditandai terkoordinasi
    org = n[n["sample_text"].str.contains("2-1 di final|gratis ongkir", case=False, regex=True)]
    assert len(org) >= 1
    assert (org["coordination"] < 70).all()
    # tidak ada kalimat jam ("pukul sembilan") yang dilabeli kekerasan
    p = res["posts"]
    assert not p[p["label"] == "Kebencian/Kekerasan"]["text"].str.contains("pukul sembilan").any()
