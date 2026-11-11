"""Uji antarmuka (Streamlit AppTest): semua halaman, interaksi utama, dan data ekstrem."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from radar import data as D

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["views/home.py", "views/narasi.py", "views/akun.py", "views/analisis_teks.py",
         "views/data_laporan.py", "views/validasi.py", "views/tentang.py"]


def _app(df=None):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.run()
    if df is not None:
        at.session_state["ds"] = {"id": f"uji{len(df)}", "name": "Unggahan: uji.csv", "source": "upload", "df": df,
                                  "anonymized": True, "warnings": []}
    return at


def _ok(at, label=""):
    assert not at.exception, f"{label}: {[e.value[:300] for e in at.exception]}"


@pytest.mark.parametrize("page", PAGES)
def test_halaman_demo_tanpa_error(page):
    at = _app()
    at.switch_page(page).run()
    _ok(at, page)


def _opsi_narasi(semua: bool):
    at = _app()
    at.switch_page("views/narasi.py").run()
    _ok(at)
    if semua:
        at.toggle[0].set_value(False).run()
        _ok(at)
    return list(at.selectbox[0].options)


def _telaah(opt: str, semua: bool):
    # instance baru per narasi: AppTest menyimpan state widget lama yang bisa hilang antar-narasi
    at = _app()
    at.switch_page("views/narasi.py").run()
    if semua:
        at.toggle[0].set_value(False).run()
    at.selectbox[0].select(opt).run()
    _ok(at, f"narasi {opt} (semua={semua})")


def test_telaah_narasi_berisiko():
    opts = _opsi_narasi(False)
    assert len(opts) >= 5
    for opt in opts:
        _telaah(opt, False)


def test_telaah_sebagian_narasi_lainnya():
    opts = _opsi_narasi(True)
    assert len(opts) >= 20
    for opt in opts[:: max(1, len(opts) // 12)]:
        _telaah(opt, True)


def test_semua_contoh_analisis_teks():
    at = _app()
    at.switch_page("views/analisis_teks.py").run()
    _ok(at)
    n = len([b for b in at.button if b.key and b.key.startswith("ex_")])
    assert n >= 6
    for i in range(n):
        btn = [b for b in at.button if b.key and b.key.startswith("ex_")][i]
        btn.click().run()
        _ok(at, f"contoh {i}")


@pytest.mark.parametrize("teks", ["", "   ", "😀", "<script>alert(1)</script> sebarkan sebelum dihapus", "a" * 4000, "hubungi 081200001234 NIK 3500000000000123"])
def test_analisis_teks_input_aneh(teks):
    at = _app()
    at.switch_page("views/analisis_teks.py").run()
    at.text_area[0].set_value(teks).run()
    _ok(at, repr(teks[:20]))


def test_replay_waktu():
    at = _app()
    at.switch_page("views/home.py").run()
    sl = at.select_slider[0]
    n = len(sl.options)           # nilai sebenarnya adalah indeks 0..n-1 (label hanya untuk tampilan)
    assert n > 10
    for i in (0, n // 4, n // 2, n - 2, n - 1):
        at.select_slider[0].set_value(i).run()
        _ok(at, f"replay {i}")


def _mini(n, same_ts=False, same_text=False):
    rows = []
    for i in range(n):
        ts = "2026-11-01 10:00:00" if same_ts else f"2026-11-01 {10 + i // 60:02d}:{i % 60:02d}:00"
        rows.append([ts, f"akun{i}", "teks sama" if same_text else f"unggahan nomor {i} biasa saja"])
    res = D.standardize(pd.DataFrame(rows, columns=["timestamp", "account_id", "text"]))
    assert res.ok
    return res.df


@pytest.mark.parametrize("n,same_ts,same_text", [(1, False, False), (2, True, True), (8, False, False), (40, True, True)])
@pytest.mark.parametrize("page", PAGES)
def test_halaman_dengan_data_kecil(page, n, same_ts, same_text):
    at = _app(_mini(n, same_ts, same_text))
    at.switch_page(page).run()
    _ok(at, f"{page} n={n}")


def test_halaman_data_laporan_parameter_dan_sumber():
    at = _app()
    at.switch_page("views/data_laporan.py").run()
    _ok(at)
    assert len(at.get("download_button")) == 4
