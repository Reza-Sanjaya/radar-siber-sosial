# Panduan Deploy (membuat Link Karya publik)

Rulebook mewajibkan **link publik yang bisa dicoba juri**. Cara gratis termudah: **Streamlit Community Cloud**.

## Langkah
1. Buat akun di https://github.com (gratis) dan akun di https://share.streamlit.io (login dengan GitHub).
2. Di GitHub: **New repository** → nama `radar-siber-sosial` → **Public** → Create.
3. Unggah seluruh isi folder proyek (tombol *uploading an existing file*; seret semua berkas & folder KECUALI `.venv`). Pastikan `requirements.txt` dan `app.py` ada di akar repo. Commit.
4. Di share.streamlit.io: **Create app** → pilih repo → Branch `main` → Main file path `app.py` → **Deploy**.
5. Tunggu 2–5 menit. Salin URL (`https://....streamlit.app`).
6. **Uji dari HP / jendela incognito**: semua 7 halaman terbuka tanpa error.
7. Opsional tetapi disarankan: di *Advanced settings* pilih Python 3.12 atau 3.13.

## Jika bermasalah
- *ModuleNotFoundError*: pastikan nama paket ada di `requirements.txt`.
- Aplikasi "tertidur" setelah lama tidak dibuka: buka URL-nya beberapa menit sebelum deadline agar aktif, lalu pastikan juri bisa membuka.
- Sebagai cadangan, tautkan juga repo GitHub (publik) pada deskripsi karya.
