"""Bangkitkan ulang data/sample_posts.csv (data sintetis/fiktif).

Jalankan dari folder proyek:
    python tools/generate_sample.py            # seed bawaan 2026
    python tools/generate_sample.py 7          # seed lain
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from radar.synth import generate_posts  # noqa: E402


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    df = generate_posts(seed=seed)
    out = ROOT / "data" / "sample_posts.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"OK: {len(df)} baris ditulis ke {out} (seed={seed})")


if __name__ == "__main__":
    main()
