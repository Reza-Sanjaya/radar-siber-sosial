@echo off
chcp 65001 >nul
title Radar Siber Sosial
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python belum terpasang. Unduh dari https://www.python.org/downloads/
  echo Saat instalasi, CENTANG "Add python.exe to PATH". Lalu jalankan ulang berkas ini.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Membuat lingkungan virtual...
  python -m venv .venv
)
echo [2/3] Memasang dependensi (pertama kali butuh beberapa menit)...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo Gagal memasang dependensi. Periksa koneksi internet lalu coba lagi.
  pause
  exit /b 1
)
echo [3/3] Menjalankan aplikasi... (peramban akan terbuka otomatis; tutup jendela ini untuk berhenti)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
