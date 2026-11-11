"""Uji pemuatan & standardisasi data: format waktu, nama kolom, encoding, anonimisasi."""
import io

import pandas as pd
import pytest

from radar import data as D


def _csv(text: str, enc: str = "utf-8") -> bytes:
    return text.encode(enc)


def test_csv_standar():
    r = D.load_csv_bytes(_csv("timestamp,account_id,text\n2026-11-01 10:00:00,a,halo\n2026-11-01 11:00:00,b,dunia\n"))
    assert r.ok and len(r.df) == 2


def test_nama_kolom_indonesia_dan_titik_koma_dan_bom():
    raw = "﻿waktu;akun;teks;pengikut\n01/11/2026 10:00;a;halo;100\n02/11/2026 10:00;b;dunia;5\n"
    r = D.load_csv_bytes(_csv(raw))
    assert r.ok, r.errors
    assert set(["timestamp", "account_id", "text", "followers"]).issubset(r.df.columns)


def test_encoding_latin1():
    r = D.load_csv_bytes("timestamp,account_id,text\n2026-11-01 10:00:00,a,café enak\n".encode("latin-1"))
    assert r.ok


@pytest.mark.parametrize("ts", ["2026-11-01T10:00:00+07:00", "2026-11-01T03:00:00Z", "1 Nov 2026 10:00", "2026-11-01", "1793527200", "1793527200000"])
def test_variasi_format_waktu(ts):
    r = D.load_csv_bytes(_csv(f"timestamp,account_id,text\n{ts},a,halo\n"))
    assert r.ok, (ts, r.errors)
    assert len(r.df) == 1


def test_kolom_wajib_hilang_memberi_pesan_jelas():
    r = D.load_csv_bytes(_csv("foo,bar\n1,2\n"))
    assert not r.ok and any("Kolom wajib" in e for e in r.errors)


@pytest.mark.parametrize("raw", [b"", b"   \n  ", b"\x00\x01\x02\xff\xfe", b"timestamp,account_id,text\n"])
def test_berkas_kosong_atau_rusak_tidak_crash(raw):
    r = D.load_csv_bytes(raw)
    assert not r.ok and r.errors


def test_baris_buruk_dibuang_dengan_peringatan():
    r = D.load_csv_bytes(_csv("timestamp,account_id,text\nbukan-tanggal,a,halo\n2026-11-01 10:00:00,b,\n2026-11-01 10:00:00,c,ok\n"))
    assert r.ok and len(r.df) == 1 and r.warnings


def test_anonimisasi_akun_dan_mention():
    r = D.load_csv_bytes(_csv("timestamp,account_id,text\n2026-11-01 10:00:00,budi_asli,halo @siti\n"), anonymize=True)
    assert r.df["account_id"].iloc[0].startswith("AKUN-")
    assert "@siti" not in r.df["text"].iloc[0]


def test_batas_baris_maksimum(monkeypatch):
    monkeypatch.setattr(D.C, "MAX_ROWS", 50)
    rows = "\n".join(f"2026-11-01 10:{i // 60:02d}:{i % 60:02d},a{i},teks {i}" for i in range(120))
    r = D.load_csv_bytes(_csv("timestamp,account_id,text\n" + rows))
    assert r.ok and len(r.df) == 50 and any("melebihi batas" in w for w in r.warnings)


def test_template_dapat_dimuat_kembali():
    r = D.load_csv_bytes(D.template_csv_bytes())
    assert r.ok and len(r.df) == 2


def test_data_demo_dimuat():
    r = D.load_sample()
    assert r.ok and len(r.df) > 1000
