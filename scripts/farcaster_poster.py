#!/usr/bin/env python3
"""
farcaster_poster.py — (OPSIONAL) Posting cast ke Farcaster lewat Neynar API.

Ini TERPISAH dari generator. Default project cuma GENERATE cast; posting otomatis
harus kamu aktifkan sendiri karena butuh signer_uuid + API key Neynar (berbayar/limit).

ENV yang dibutuhkan:
    NEYNAR_API_KEY     API key dari https://neynar.com
    NEYNAR_SIGNER_UUID signer_uuid akun Farcaster kamu (dari Neynar managed signers)

Contoh:
    echo "gm farcaster" | python scripts/farcaster_poster.py
    python scripts/farcaster_poster.py --text "cast dari script"
    python scripts/farcaster_poster.py --dry-run --text "cek dulu tanpa posting"

SAFETY: pakai --dry-run untuk melihat payload tanpa benar-benar memposting.
Jangan pernah commit NEYNAR_API_KEY / SIGNER_UUID ke repo.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
SIGNER_UUID = os.getenv("NEYNAR_SIGNER_UUID", "")
CAST_ENDPOINT = "https://api.neynar.com/v2/farcaster/cast"
MAX_CAST_LEN = 320


def post_cast(text: str, dry_run: bool = False, timeout: int = 30) -> dict:
    text = text.strip()
    if not text:
        sys.exit("ERROR: teks cast kosong.")
    if len(text) > MAX_CAST_LEN:
        sys.exit(f"ERROR: cast {len(text)} char > {MAX_CAST_LEN} (batas Farcaster).")

    payload = {"signer_uuid": SIGNER_UUID, "text": text}

    if dry_run:
        return {"dry_run": True, "would_post": payload}

    if not NEYNAR_API_KEY or not SIGNER_UUID:
        sys.exit("ERROR: set NEYNAR_API_KEY dan NEYNAR_SIGNER_UUID dulu.")

    req = urllib.request.Request(
        CAST_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "api_key": NEYNAR_API_KEY,   # header Neynar v2
            "x-api-key": NEYNAR_API_KEY, # kompat versi baru
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        sys.exit(f"ERROR posting ke Neynar: {e}")


def main():
    ap = argparse.ArgumentParser(description="Post 1 cast ke Farcaster via Neynar.")
    ap.add_argument("--text", help="Teks cast. Jika kosong, dibaca dari stdin.")
    ap.add_argument("--dry-run", action="store_true", help="Tampilkan payload tanpa posting.")
    args = ap.parse_args()

    text = args.text if args.text else sys.stdin.read()
    result = post_cast(text, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
