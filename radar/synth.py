"""Generator data SINTETIS (100% fiktif) untuk demo & pengujian.

Tidak ada akun, nama, nomor telepon, atau peristiwa nyata. Seluruh akun adalah alias
acak; nomor telepon & NIK pada skenario doxxing adalah angka rekaan yang tidak valid.

Skenario yang disisipkan di antara percakapan latar:
    A  hoaks "posko bantuan ditutup" - kampanye terkoordinasi (akun baru, waktu serentak)
    B  provokasi/adu domba terhadap kelompok FIKTIF 'Golongan X' (tanpa identitas nyata)
    C  penipuan rekrutmen yang mencatut institusi - spam berulang dari akun yang sama
    D  doxxing (data rekaan) - ajakan menggeruduk
    E  klarifikasi resmi + warga meluruskan (konten benign yang tidak boleh ditandai)
    F  dua topik ORGANIK yang viral wajar (olahraga, diskon) - kontrol: bukan koordinasi
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

START = pd.Timestamp("2026-10-31 00:00:00")
DAYS = 7

PLATFORMS = ["X", "Facebook", "Instagram", "TikTok"]
PLATFORM_P = [0.5, 0.25, 0.15, 0.10]

KOTA = ["kota ini", "daerah kita", "wilayah timur", "pusat kota", "area kampus"]
CUACA = ["cerah berawan", "mendung tipis", "gerimis", "panas terik", "sejuk"]
TIM = ["tim kebanggaan kita", "klub lokal", "tim kampus", "tim kesayangan"]
MAKAN = ["soto", "nasi goreng", "bakso", "gado-gado", "sate bakar", "kopi susu", "mie ayam"]

BACKGROUND = [
    "Cuaca {kota} hari ini {cuaca}, jangan lupa bawa payung ya.",
    "Semalam hasil pertandingan seru banget, {tim} menang tipis.",
    "Baru coba {makan} di dekat kampus, enak banget dan harganya bersahabat.",
    "Tugas kuliah minggu ini numpuk, semangat semuanya yang lagi begadang.",
    "Ada bakti sosial komunitas di balai warga hari Minggu, yuk ikut membantu!",
    "Ayo kumpul di lapangan, bersih-bersih lingkungan bareng warga sekitar.",
    "Lalu lintas {kota} padat di jam pulang kantor, sebaiknya berangkat lebih awal.",
    "Update aplikasi terbaru bikin baterai cepat habis, ada yang ngalamin juga?",
    "Video kucing viral itu lucu banget, nonton sampai tiga kali.",
    "Prajurit membantu evakuasi warga saat banjir kemarin, terima kasih atas kerja kerasnya.",
    "Pameran alutsista di alun-alun ramai pengunjung, anak-anak senang sekali.",
    "Diskon akhir bulan di toko favorit, gratis ongkir untuk pembelian tertentu.",
    "Belajar pemrograman dari nol ternyata asyik kalau rutin latihan tiap hari.",
    "Webinar keamanan siber kemarin bermanfaat, jadi paham cara membuat kata sandi yang kuat.",
    "Perpustakaan kota menambah koleksi buku baru, cocok untuk mahasiswa.",
    "Tolong rekomendasikan tempat servis laptop yang terpercaya di sekitar sini.",
    "Selamat pagi semuanya, semoga hari ini penuh berkah dan lancar urusannya.",
    "Pemerintah daerah meresmikan taman baru, suasananya adem untuk jalan sore.",
    "Harga cabai mulai turun, ibu-ibu pasar bilang stok cukup minggu ini.",
    "Rapat komunitas malam ini membahas jadwal kegiatan bulan depan.",
    "Kemarin ikut latihan lari pagi 5K, capek tapi puas banget.",
    "Hati-hati di jalan, ada pohon tumbang di dekat pertigaan, mohon pelan-pelan.",
    "Kuliah umum tentang literasi digital menarik, banyak tips mengenali hoaks.",
    "Rekrutmen resmi dibuka lewat situs panitia, cek jadwal dan persyaratan dengan teliti.",
    "Mohon doanya untuk teman-teman yang sedang ujian hari ini.",
]

FILLERS = [
    "Besok ada jadwal padat di kantor.", "Tadi sempat mampir ke toko buku.", "Jalanan licin habis hujan deras.",
    "Teman sekelas ngajak kerja kelompok.", "Listrik sempat padam sebentar tadi sore.", "Sinyal internet lagi lemot banget.",
    "Kopi hangat cocok buat sore ini.", "Anak-anak main layangan di lapangan.", "Harga bensin masih stabil minggu ini.",
    "Ada pasar malam di dekat stasiun.", "Motor baru selesai diservis kemarin.", "Pagi tadi kereta terlambat sepuluh menit.",
    "Wifi kos sering putus nyambung.", "Dosen pembimbing minta revisi bab dua.", "Sedang menunggu paket dari kurir.",
    "Tetangga sebelah baru pindahan rumah.", "Konser musik akhir pekan bakal ramai.", "Resep ibu paling juara dari dulu.",
    "Lagi belajar bahasa asing lewat aplikasi.", "Ujian praktikum dimajukan hari Kamis.", "Sepeda lipat baru akhirnya datang.",
    "Warung langganan tutup lebih awal hari ini.", "Pemandangan sore dari lantai atas indah sekali.",
    "Baterai ponsel tinggal sedikit lagi.", "Rencana liburan masih belum pasti.", "Kucing di rumah makin gemuk saja.",
    "Banyak daun berguguran di halaman.", "Tadi malam bintang kelihatan jelas.", "Antrean di kasir lumayan panjang.",
    "Lampu jalan di gang sudah diganti.", "Kelas daring dimulai pukul sembilan.", "Stok buku catatan hampir habis.",
    "Percobaan kimia kemarin berhasil juga.", "Pohon mangga depan rumah mulai berbuah.", "Rapat selesai lebih cepat dari jadwal.",
    "Tukang parkir ramah banget tadi.", "Hujan reda, langit mulai cerah lagi.", "Jadwal kereta berubah mulai bulan depan.",
    "Es teh manis memang penyelamat siang bolong.", "Grup kuliah ramai bahas tugas akhir.",
]

ORGANIC_TOPICS = {
    "bola": [
        "Selamat untuk {tim}, menang 2-1 di final semalam! Bangga banget!",
        "Akhirnya {tim} juara, menang 2-1 di final, luar biasa perjuangannya!",
        "Menang 2-1 di final, {tim} layak juara. Bangga sekali semalam!",
    ],
    "diskon": [
        "Diskon besar belanja online akhir bulan, gratis ongkir seluruh kota, cek aplikasinya sekarang!",
        "Belanja online lagi diskon akhir bulan nih, gratis ongkir untuk semua kota, buruan cek aplikasinya!",
    ],
}

CAMPAIGN_A_BASE = [
    "VIRAL!!! Markas satuan menutup posko bantuan banjir, media bungkam! Sebarkan sebelum dihapus!!!",
    "Info rahasia dari orang dalam: posko bantuan banjir ditutup permanen dan bantuan ditahan, media tidak berani memberitakan. Sebarkan!",
    "Heboh! Posko bantuan korban banjir katanya ditutup oleh satuan, pemerintah menutupi. Tolong sebarkan sebelum diblokir.",
]
CAMPAIGN_A_PRE = [
    "Katanya posko bantuan banjir mau ditutup, ada yang tahu kabar benarnya?",
    "Kabarnya bantuan banjir ditahan, kok media tidak ada yang memberitakan ya?",
]
CAMPAIGN_B_BASE = [
    "Golongan X biang kerok semua masalah di daerah ini, kita atau mereka! Ayo turun ke jalan malam ini, saatnya bergerak!",
    "Golongan X itu musuh bersama, boikot dan usir dari daerah ini, ayo bangkit melawan serentak!",
    "Warga kita dibiarkan saja dirugikan golongan X, bangkit melawan, ayo kumpul di alun-alun malam ini!",
]
CAMPAIGN_B_VIOLENT = [
    "Sudah saatnya kita serbu dan hancurkan posko golongan X, ayo serentak sekarang juga!",
    "Ayo geruduk dan kepung kantor golongan X malam ini, waktunya bergerak serentak!",
    "Hancurkan pos mereka, ayo ramai-ramai serbu malam ini!",
]
CAMPAIGN_C_BASE = [
    "Lulus tanpa tes! Jalur khusus rekrutmen TNI AD, biaya administrasi transfer ke rekening 0000123456, hubungi admin klik {link}",
    "Rekrutmen TNI AD jalur belakang, jaminan lulus, bayar biaya seleksi lewat rekening 0000123456 lalu klik {link}",
    "Pasti lulus seleksi bintara lewat calo terpercaya, transfer biaya pendaftaran dulu ya, daftar di {link}",
]
CAMPAIGN_D_BASE = [
    "Ini alamat lengkap dan no hp Pak Fulan {phone}, NIK {nik}. Ayo geruduk rumahnya, sebarkan data ini!",
    "Sebar data Pak Fulan: alamat rumah ada di grup, no hp {phone}, NIK {nik}. Ayo cari dan geruduk!",
]
CAMPAIGN_E_OFFICIAL = [
    "KLARIFIKASI: Kabar posko bantuan banjir ditutup adalah hoaks. Faktanya posko tetap beroperasi 24 jam. Sumber: rilis resmi satuan.",
    "Cek fakta: informasi penutupan posko bantuan tidak benar. Posko tetap melayani warga, sumber: pernyataan resmi.",
]
CAMPAIGN_E_CITIZEN = [
    "Ternyata kabar posko ditutup itu hoaks, faktanya posko tetap buka. Mohon jangan sebarkan kabar bohong ya.",
    "Sudah dicek, informasi posko bantuan ditutup tidak benar. Jangan sebarkan hoaks, tunggu informasi resmi.",
]
SPAM_BASE = [
    "Slot gacor hari ini, klik link {link}, deposit receh langsung cuan, judi online terpercaya!",
    "Pinjol cepat cair tanpa jaminan, modal receh, klik link {link} sekarang juga!",
]

PREFIX = ["", "", "Tolong share:", "Jangan percaya media!", "Bagikan ke semua grup!", "PENTING:", "Waspada!", "Info:"]
SUFFIX = ["", "", "", "Sebarkan seluas-luasnya!", "Bagikan sebelum hilang.", "Jangan sampai terlewat!"]
EMOJI = ["", "", "", " \U0001F525", " ⚠️", " \U0001F6A8", " \U0001F4E2"]


def _hex_id(rng: np.random.Generator, seen: set[str]) -> str:
    while True:
        h = hashlib.sha1(str(rng.integers(0, 2**62)).encode()).hexdigest()[:6].upper()
        ident = f"AKUN-{h}"
        if ident not in seen:
            seen.add(ident)
            return ident


def _make_accounts(rng, seen, n, kind) -> list[dict]:
    out = []
    for _ in range(n):
        if kind == "organic":
            age = float(np.clip(rng.lognormal(6.4, 0.9), 60, 4500))
            followers = float(np.clip(rng.lognormal(5.6, 1.2), 15, 90000))
            following = float(np.clip(rng.lognormal(5.3, 0.8), 20, 1500))
        elif kind == "bot":
            age = float(rng.integers(1, 26))
            followers = float(rng.integers(3, 80))
            following = float(rng.integers(600, 3000))
        elif kind == "scam":
            age = float(rng.integers(3, 40))
            followers = float(rng.integers(10, 200))
            following = float(rng.integers(500, 2500))
        elif kind == "official":
            age = float(rng.integers(1500, 3000))
            followers = float(rng.integers(40000, 120000))
            following = float(rng.integers(50, 300))
        else:  # spam
            age = float(rng.integers(10, 120))
            followers = float(rng.integers(20, 400))
            following = float(rng.integers(300, 1800))
        out.append(
            {
                "id": _hex_id(rng, seen),
                "platform": str(rng.choice(PLATFORMS, p=PLATFORM_P)),
                "age": round(age),
                "followers": round(followers),
                "following": round(following),
            }
        )
    return out


def _variant(rng, base: str, *, caps: float = 0.12, drop: float = 0.5, tags: list[str] | None = None) -> str:
    words = base.split()
    if len(words) > 8 and rng.random() < drop:
        i = int(rng.integers(3, len(words) - 2))
        words.pop(i)
    core = " ".join(words)
    if rng.random() < caps:
        core = core.upper()
    prefix = str(rng.choice(PREFIX))
    suffix = str(rng.choice(SUFFIX))
    emoji = str(rng.choice(EMOJI))
    hashtags = ""
    if tags:
        k = int(rng.integers(1, len(tags) + 1))
        chosen = list(rng.choice(tags, size=k, replace=False))
        hashtags = " " + " ".join(chosen)
    return " ".join(p for p in (prefix, core, suffix) if p).strip() + emoji + hashtags


def _hour_weights() -> np.ndarray:
    w = np.full(24, 0.3)
    for h, v in {6: 1.2, 7: 2.0, 8: 2.2, 9: 1.6, 11: 1.4, 12: 2.0, 13: 1.8, 16: 1.5, 18: 1.8,
                 19: 2.2, 20: 2.6, 21: 2.8, 22: 2.2, 23: 1.0}.items():
        w[h] = v
    return w / w.sum()


def generate_posts(seed: int = 2026, n_background: int = 1100) -> pd.DataFrame:
    """Hasilkan DataFrame kanonik (kolom sama dengan `radar.data.ALL_COLUMNS`)."""
    rng = np.random.default_rng(int(seed))
    seen: set[str] = set()
    organic = _make_accounts(rng, seen, 420, "organic")
    bots = _make_accounts(rng, seen, 70, "bot")
    scam = _make_accounts(rng, seen, 8, "scam")
    official = _make_accounts(rng, seen, 3, "official")
    spam = _make_accounts(rng, seen, 3, "spam")
    rows: list[dict] = []

    def add(acc: dict, ts: pd.Timestamp, text: str, likes: int, shares: int, replies: int) -> None:
        rows.append(
            {
                "timestamp": ts.floor("s"),
                "platform": acc["platform"],
                "account_id": acc["id"],
                "text": text,
                "likes": int(max(likes, 0)),
                "shares": int(max(shares, 0)),
                "replies": int(max(replies, 0)),
                "followers": acc["followers"],
                "following": acc["following"],
                "account_age_days": acc["age"],
            }
        )

    def engagement(scale: float) -> tuple[int, int, int]:
        likes = int(rng.lognormal(np.log(max(scale, 0.5)), 1.0))
        shares = int(likes * rng.uniform(0.05, 0.4))
        replies = int(likes * rng.uniform(0.02, 0.2))
        return likes, shares, replies

    hour_p = _hour_weights()
    zipf_w = 1.0 / np.arange(1, len(organic) + 1) ** 0.6
    zipf_w /= zipf_w.sum()

    def organic_time(day_lo: int = 0, day_hi: int = DAYS) -> pd.Timestamp:
        day = int(rng.integers(day_lo, day_hi))
        hour = int(rng.choice(24, p=hour_p))
        return START + pd.Timedelta(days=day, hours=hour, minutes=int(rng.integers(0, 60)), seconds=int(rng.integers(0, 60)))

    # ---- latar organik ---------------------------------------------------
    for _ in range(n_background):
        acc = organic[int(rng.choice(len(organic), p=zipf_w))]
        tpl = str(rng.choice(BACKGROUND))
        text = tpl.format(
            kota=rng.choice(KOTA), cuaca=rng.choice(CUACA), tim=rng.choice(TIM), makan=rng.choice(MAKAN)
        )
        if rng.random() < 0.85:  # variasi alami agar percakapan latar tidak identik
            extra = rng.choice(FILLERS, size=2, replace=False)
            text = f"{text} {extra[0]} {extra[1]}"
        add(acc, organic_time(), text, *engagement(4))

    # ---- F: topik organik viral wajar (kontrol) --------------------------------
    for topic, templates in ORGANIC_TOPICS.items():
        day = 4 if topic == "bola" else 2
        n = 48 if topic == "bola" else 36
        for _ in range(n):
            acc = organic[int(rng.integers(0, len(organic)))]
            hour = float(np.clip(rng.normal(21 if topic == "bola" else 14, 3.5), 6, 23.5))
            ts = START + pd.Timedelta(days=day, hours=hour)
            text = str(rng.choice(templates)).format(tim=rng.choice(TIM))
            add(acc, ts, text, *engagement(8))

    # ---- A: kampanye hoaks posko (terkoordinasi) -----------------------------
    a_start = START + pd.Timedelta(days=6, hours=17, minutes=30)
    a_accounts = bots[:38]
    a_organic_amp = organic[:6]
    for acc in a_accounts[:20]:  # prekursor ringan pada pagi hari
        ts = START + pd.Timedelta(days=6, hours=8, minutes=int(rng.integers(0, 240)))
        add(acc, ts, _variant(rng, str(rng.choice(CAMPAIGN_A_PRE)), caps=0.0, drop=0.2), *engagement(1))
    for i in range(55):
        acc = a_accounts[i % len(a_accounts)] if i < 48 else a_organic_amp[i % len(a_organic_amp)]
        ts = a_start + pd.Timedelta(minutes=float(rng.beta(1.2, 3.0) * 100))
        likes, shares, replies = engagement(2 if i < 48 else 40)
        add(acc, ts, _variant(rng, str(rng.choice(CAMPAIGN_A_BASE)), tags=["#PoskoDitutup", "#MediaBungkam", "#SebarkanFakta"]),
            likes, shares, replies)

    # ---- B: provokasi SARA / adu domba ----------------------------------------------
    b_accounts = bots[40:52] + organic[10:20]
    for i in range(40):
        acc = b_accounts[int(rng.integers(0, len(b_accounts)))]
        ts = START + pd.Timedelta(days=5, hours=12) + pd.Timedelta(hours=float(rng.uniform(0, 34)))
        add(acc, ts, _variant(rng, str(rng.choice(CAMPAIGN_B_BASE)), caps=0.05, tags=["#KitaAtauMereka", "#BangkitMelawan"]),
            *engagement(30))
    for base in CAMPAIGN_B_VIOLENT:
        acc = organic[int(rng.integers(20, 60))]
        ts = START + pd.Timedelta(days=6, hours=int(rng.integers(19, 23)), minutes=int(rng.integers(0, 60)))
        add(acc, ts, base, *engagement(12))

    # ---- C: penipuan rekrutmen (spam berulang akun sama) ------------------------------
    links = ["bit.ly/daftarkhusus", "bit.ly/lulus-instan", "s.id/rekrut-cepat"]
    for _ in range(30):
        acc = scam[int(rng.integers(0, len(scam)))]
        ts = START + pd.Timedelta(days=int(rng.integers(2, 6)), hours=int(rng.integers(8, 23)), minutes=int(rng.integers(0, 60)))
        text = str(rng.choice(CAMPAIGN_C_BASE)).format(link=rng.choice(links))
        add(acc, ts, text + str(rng.choice(EMOJI)), *engagement(2))

    # ---- D: doxxing (data rekaan) ---------------------------------------------------
    d_accounts = organic[60:65]
    for _ in range(8):
        acc = d_accounts[int(rng.integers(0, len(d_accounts)))]
        ts = START + pd.Timedelta(days=6, hours=9, minutes=int(rng.integers(0, 120)))
        text = str(rng.choice(CAMPAIGN_D_BASE)).format(phone="081200001234", nik="3500000000000123")
        add(acc, ts, text, *engagement(6))

    # ---- E: klarifikasi & literasi ------------------------------------------------------
    e_start = START + pd.Timedelta(days=6, hours=19, minutes=40)
    for i in range(6):
        acc = official[i % len(official)]
        ts = e_start + pd.Timedelta(minutes=float(rng.uniform(0, 200)))
        add(acc, ts, str(rng.choice(CAMPAIGN_E_OFFICIAL)), *engagement(60))
    for _ in range(19):
        acc = organic[int(rng.integers(100, 300))]
        ts = e_start + pd.Timedelta(minutes=float(rng.uniform(5, 260)))
        add(acc, ts, str(rng.choice(CAMPAIGN_E_CITIZEN)), *engagement(10))

    # ---- spam judi/pinjol ----------------------------------------------------------------
    spam_links = ["bit.ly/slot-hoki", "s.id/pinjol-kilat"]
    for _ in range(12):
        acc = spam[int(rng.integers(0, len(spam)))]
        ts = organic_time(1, 7)
        add(acc, ts, str(rng.choice(SPAM_BASE)).format(link=rng.choice(spam_links)), *engagement(1))

    df = pd.DataFrame(rows).sort_values("timestamp", kind="stable").reset_index(drop=True)
    df.insert(0, "post_id", [f"P{i:06d}" for i in range(1, len(df) + 1)])
    return df[["post_id", "timestamp", "platform", "account_id", "text", "likes", "shares", "replies",
               "followers", "following", "account_age_days"]]
