"""Uji mesin analisis teks: kategori, negasi, klarifikasi, penyamaran data pribadi."""
import pytest

from radar import constants as C
from radar.analyzer import analyze_text, highlight_html
from radar.text_utils import find_pii, mask_pii, normalize, safe_text


def test_hoaks_sensasional_berisiko_tinggi():
    r = analyze_text("VIRAL!!! Markas satuan menutup posko bantuan banjir, media bungkam! Sebarkan sebelum dihapus!!!")
    assert r["label"] == C.CAT_DISINFO
    assert r["risk"] >= 60
    assert r["tni_relevant"]


def test_penipuan_rekrutmen_mencatut_institusi():
    r = analyze_text("Lulus tanpa tes! Jalur khusus rekrutmen TNI AD, biaya administrasi transfer ke rekening 0000123456, klik bit.ly/daftarkhusus")
    assert r["label"] == C.CAT_PENIPUAN
    assert r["risk"] >= 70
    assert r["tni_target"]


def test_provokasi_kelompok_fiktif():
    r = analyze_text("Golongan X biang kerok semua masalah, kita atau mereka! Boikot dan usir dari daerah ini, ayo turun ke jalan malam ini!")
    assert r["label"] == C.CAT_PROVOKASI
    assert r["risk"] >= 50


def test_doxxing_data_rekaan_tersamarkan():
    teks = "Ini alamat lengkap dan no hp Pak Fulan 081200001234, NIK 3500000000000123. Ayo geruduk rumahnya, sebarkan data ini!"
    r = analyze_text(teks)
    assert r["label"] == C.CAT_DOXXING
    assert r["pii"]["nik"] == 1 and r["pii"]["phone"] == 1
    masked = mask_pii(teks)
    assert "3500000000000123" not in masked and "081200001234" not in masked


def test_klarifikasi_tidak_ditandai_sebagai_hoaks():
    r = analyze_text("KLARIFIKASI: Kabar posko bantuan banjir ditutup adalah hoaks. Faktanya posko tetap beroperasi 24 jam. Sumber: rilis resmi satuan.")
    assert r["label"] == C.CAT_KLARIFIKASI
    assert r["risk"] < C.BINARY_RISK_THRESHOLD


@pytest.mark.parametrize("teks", [
    "Besok ada rapat komunitas pukul 19.00 di balai warga, mohon hadir tepat waktu.",
    "Kelas daring dimulai pukul sembilan, jangan lupa bawa laptop.",
    "Sate bakar di dekat alun-alun enak banget.",
    "Pemadam kebakaran berhasil memadamkan api di pasar, tidak ada korban jiwa.",
    "Jangan bunuh waktu dengan scroll medsos terus, mending baca buku.",
    "Ayo kumpul di lapangan, bersih-bersih lingkungan bareng warga sekitar.",
    "Prajurit membantu evakuasi warga saat banjir kemarin, terima kasih atas kerja kerasnya.",
])
def test_kalimat_wajar_tidak_salah_tandai(teks):
    assert analyze_text(teks)["risk"] < 20


def test_negasi_menurunkan_skor():
    positif = analyze_text("Ayo serbu dan hancurkan posko mereka malam ini")["risk"]
    negasi = analyze_text("Jangan serbu dan jangan hancurkan posko, kami kecam kekerasan")["risk"]
    assert negasi < positif


@pytest.mark.parametrize("nilai", [None, float("nan"), "", "   ", 12345, "😀😀😀", "!!!???", "a" * 20000, "\x00\x01\x02", "<script>alert(1)</script>"])
def test_input_aneh_tidak_membuat_error(nilai):
    r = analyze_text(nilai)
    assert 0.0 <= r["risk"] <= 100.0
    assert r["label"] in C.ALL_LABELS


def test_highlight_html_meloloskan_html_berbahaya():
    teks = "<script>alert('x')</script> SEBARKAN sebelum dihapus <img src=x onerror=alert(1)>"
    r = analyze_text(teks)
    out = highlight_html(r["norm"], r["cues"])
    assert "<script>" not in out and "<img" not in out


def test_normalisasi_dan_safe_text():
    assert safe_text(None) == "" and safe_text(float("nan")) == ""
    assert "heboh" in normalize("HEBOOOOH banget")
    assert find_pii("hubungi 081200001234")["phone"] == 1
